"""
Sparrow Enterprise Server Installation Agent
=============================================
터미널 기반 CLI 에이전트 - 메인 진입점

Usage:
    python main.py
"""
import io
import os
import sys

# ── Windows 터미널 UTF-8 강제 설정 ──────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text
from rich.rule import Rule

from agent import __version__
from agent.config import AgentConfig
from agent.cli import collect_user_input
from agent.checks.permissions import check_permissions
from agent.checks.ports import check_ports
from agent.checks.packages import check_packages
from agent.installer.extractor import extract_package
from agent.installer.properties import patch_properties
from agent.installer.profiles import patch_profiles
from agent.installer.runner import run_server
from agent.llm.base import create_llm_client
from agent.utils.network import get_local_ipv4

console = Console(force_terminal=True, legacy_windows=False)


BANNER = r"""
   ____                                        ___                    __
  / __/ ___  ___ _ ____ ____ ___  _    __ _    / _ | ___ _ ___  ___  / /_
 _\ \  / _ \/ _ `// __// __// _ \| |/|/ // /  / __ |/ _ `// -_)/ _ \/ __/
/___/ / .__/\_,_//_/  /_/   \___/|__,__//_/  /_/ |_|\_,_/ \__//_//_/\__/
     /_/
"""


def print_banner():
    """에이전트 배너를 출력합니다."""
    console.print(
        Panel(
            Text(BANNER, style="bold cyan")
            + Text(
                f"\n  Sparrow Enterprise Server Installation Agent v{__version__}\n"
                "  Automated Installation Pipeline with LLM Intelligence\n",
                style="dim",
            ),
            border_style="bright_blue",
            padding=(0, 2),
        )
    )


def print_step(step_num: int, total: int, description: str):
    """파이프라인 단계 헤더를 출력합니다."""
    console.print()
    console.print(Rule(
        f"[bold bright_blue]STEP {step_num}/{total}[/bold bright_blue]  {description}",
        style="bright_blue",
    ))
    console.print()


def ask_continue(message: str = "다음 단계로 진행하시겠습니까?") -> bool:
    """사용자에게 계속 진행 여부를 묻습니다."""
    console.print()
    return Confirm.ask(f"  {message}", default=True)


def main():
    """메인 실행 함수"""
    try:
        # ── 배너 출력 ──
        print_banner()

        # ── 설정 객체 초기화 ──
        config = AgentConfig()
        console.print(
            f"  [OS]  감지된 OS: [bold]{config.os_type.value.upper()}[/bold]",
            style="dim",
        )
        console.print()

        # ══════════════════════════════════════════════════════════════
        # STEP 1: 사전 환경 점검
        # ══════════════════════════════════════════════════════════════
        print_step(1, 5, "사전 환경 점검")

        # 1-1. 권한 검증
        console.print("  [bold]1-1. 실행 권한 검증[/bold]")
        if not check_permissions(config):
            sys.exit(1)

        # 1-2. 포트 충돌 검사
        console.print()
        console.print("  [bold]1-2. 포트 충돌 검사[/bold]")
        if not check_ports():
            sys.exit(1)

        console.print()
        console.print(
            "  [bold green]사전 환경 점검 완료.[/bold green] "
            "권한 및 포트 상태 모두 정상입니다.",
        )
        if not ask_continue("설치 설정 입력을 시작하시겠습니까?"):
            console.print("  설치가 취소되었습니다.", style="yellow")
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 2: 사용자 입력 수집
        # ══════════════════════════════════════════════════════════════
        print_step(2, 5, "설치 설정 입력")

        if not collect_user_input(config):
            console.print("\n  [FAIL] 설정이 취소되었습니다.", style="red")
            sys.exit(1)

        # LLM 클라이언트 생성
        llm_client = create_llm_client(config.llm_provider, config.api_key)

        # IP 추출
        console.print("  >> 네트워크 IP 추출 중...", style="dim")
        local_ip = get_local_ipv4()
        if not local_ip:
            console.print(Panel(
                "[bold red][ERROR] 네트워크 IP를 식별할 수 없습니다. "
                "연결 상태를 확인하세요.[/bold red]",
                title="[ERR] 네트워크 오류",
                border_style="red",
            ))
            sys.exit(1)
        config.local_ip = local_ip
        console.print(f"  [ OK ] 로컬 IP: [bold]{local_ip}[/bold]", style="green")

        # ══════════════════════════════════════════════════════════════
        # STEP 3: 패키지 압축 해제
        # ══════════════════════════════════════════════════════════════
        print_step(3, 5, "패키지 압축 해제")
        console.print(
            f"  >> 설치 경로: [bold]{config.install_dir}[/bold]",
            style="dim",
        )
        console.print(
            f"  >> ZIP 파일: [bold]{config.package_path.name}[/bold]",
            style="dim",
        )
        console.print(
            f"  >> 대상 디렉터리: [bold]{config.install_dir / config.package_path.stem}[/bold]",
            style="dim",
        )
        console.print()

        if not extract_package(config):
            console.print("  [FAIL] 패키지 압축 해제 실패", style="red")
            sys.exit(1)

        # 압축 해제 직후 prerequisite/vc_redist 확인
        console.print()
        console.print("  [bold]prerequisite 패키지 확인[/bold]")
        pkg_ok = check_packages(config)
        if not pkg_ok:
            console.print(
                "  [WARN] VC++ Redistributable 설치 실패. "
                "일부 기능이 제한될 수 있습니다.",
                style="yellow",
            )
            if not ask_continue("패키지 문제가 있습니다. 그래도 계속 진행하시겠습니까?"):
                sys.exit(0)
        else:
            if not ask_continue("압축 해제 완료. Properties 자동 구성을 진행하시겠습니까?"):
                sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 4: sparrow.properties 자동 구성
        # ══════════════════════════════════════════════════════════════
        print_step(4, 5, "sparrow.properties 자동 구성")
        console.print(
            f"  >> 대상 파일: [bold]{config.base_dir / 'sparrow.properties'}[/bold]",
            style="dim",
        )
        console.print()

        if not patch_properties(config):
            console.print("  [FAIL] Properties 패치 실패", style="red")
            sys.exit(1)

        if not ask_continue("Properties 구성 완료. DB 프로파일 패치를 진행하시겠습니까?"):
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 5: DB 프로파일 다국어 패치
        # ══════════════════════════════════════════════════════════════
        print_step(5, 5, "DB 프로파일 다국어 패치")

        if not patch_profiles(config, llm_client):
            console.print(
                "  [WARN] 프로파일 패치에 일부 문제가 발생했습니다.",
                style="yellow",
            )

        if not ask_continue("DB 프로파일 패치 완료. 서버 설치 및 구동을 시작하시겠습니까?"):
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 6: 서비스 설치 및 구동
        # ══════════════════════════════════════════════════════════════
        print_step(5, 5, "서비스 설치 및 구동")
        console.print(
            f"  >> BASE_DIR: [bold]{config.base_dir}[/bold]",
            style="dim",
        )
        console.print(
            "  >> 설치 순서: install 스크립트 → start 스크립트",
            style="dim",
        )
        console.print()

        if run_server(config, llm_client):
            console.print()
            modules_str = (
                ", ".join(m.upper() for m in config.enabled_optional_modules)
                if config.enabled_optional_modules else "없음"
            )
            console.print(Panel(
                "[bold green]Sparrow Enterprise Server 설치가 완료되었습니다![/bold green]\n\n"
                f"  설치 경로  : {config.base_dir}\n"
                f"  접속 주소  : http://{config.local_ip}:{10880}\n"
                f"  언어 설정  : {config.language.value}\n"
                f"  활성 모듈  : {modules_str}\n"
                f"  LLM 제공자 : {llm_client.get_provider_name()}",
                title="[ DONE ] 설치 완료",
                border_style="green",
                padding=(1, 2),
            ))
            _wait_if_exe()
        else:
            console.print()
            console.print(Panel(
                "[bold red]서버 구동에 실패하였습니다.[/bold red]\n\n"
                "위의 오류 분석 리포트를 참고하여 문제를 해결하세요.\n"
                "문제 해결 후 에이전트를 다시 실행할 수 있습니다 (멱등성 지원).",
                title="[FAIL] 설치 실패",
                border_style="red",
                padding=(1, 2),
            ))
            _wait_if_exe()
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n  [WARN] 사용자에 의해 중단되었습니다.", style="yellow")
        _wait_if_exe()
        sys.exit(130)
    except Exception as e:
        console.print(f"\n  [FAIL] 예기치 않은 오류: {e}", style="bold red")
        console.print_exception(show_locals=False)
        _wait_if_exe()
        sys.exit(1)


def _wait_if_exe():
    """
    PyInstaller로 빌드된 exe 더블클릭 실행 시
    창이 즉시 닫히지 않도록 Enter 대기합니다.
    일반 터미널 실행에서는 동작하지 않습니다.
    """
    if getattr(sys, "frozen", False):
        console.print()
        console.print("[dim]계속하려면 Enter 키를 누르세요...[/dim]")
        try:
            input()
        except Exception:
            pass


if __name__ == "__main__":
    main()
