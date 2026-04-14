"""
Sparrow Enterprise Server Installation Agent
=============================================
터미널 기반 CLI 에이전트 - 메인 진입점

Usage:
    python main.py
"""
import sys

# ── Windows 터미널 UTF-8 강제 설정 ──────────────────────────────────────
if sys.platform == "win32":
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

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


BANNER = r"""
   ____                                        ___                    __
  / __/ ___  ___ _ ____ ____ ___  _    __ _    / _ | ___ _ ___  ___  / /_
 _\ \  / _ \/ _ `// __// __// _ \| |/|/ // /  / __ |/ _ `// -_)/ _ \/ __/
/___/ / .__/\_,_//_/  /_/   \___/|__,__//_/  /_/ |_|\_,_/ \__//_//_/\__/
     /_/
"""


def print_banner():
    print("=" * 70)
    print(BANNER)
    print(f"  Sparrow Enterprise Server Installation Agent v{__version__}")
    print("  Automated Installation Pipeline with LLM Intelligence")
    print("=" * 70)


def print_step(step_num: int, total: int, description: str):
    print()
    print("=" * 70)
    print(f"  STEP {step_num}/{total}  {description}")
    print("=" * 70)
    print()


def ask_continue(message: str = "다음 단계로 진행하시겠습니까?") -> bool:
    print()
    while True:
        ans = input(f"  {message} [Y/n]: ").strip().lower()
        if not ans or ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  y 또는 n을 입력하세요.")


def main():
    try:
        print_banner()

        config = AgentConfig()
        print(f"  감지된 OS: {config.os_type.value.upper()}")
        print()

        # ══════════════════════════════════════════════════════════════
        # STEP 1: 사전 환경 점검
        # ══════════════════════════════════════════════════════════════
        print_step(1, 5, "사전 환경 점검")

        print("  1-1. 실행 권한 검증")
        if not check_permissions(config):
            sys.exit(1)

        print()
        print("  1-2. 포트 충돌 검사")
        if not check_ports():
            sys.exit(1)

        print()
        print("  사전 환경 점검 완료. 권한 및 포트 상태 모두 정상입니다.")
        if not ask_continue("설치 설정 입력을 시작하시겠습니까?"):
            print("  설치가 취소되었습니다.")
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 2: 사용자 입력 수집
        # ══════════════════════════════════════════════════════════════
        print_step(2, 5, "설치 설정 입력")

        if not collect_user_input(config):
            print("\n  [FAIL] 설정이 취소되었습니다.")
            sys.exit(1)

        llm_client = create_llm_client(config.llm_provider, config.api_key)

        print("  >> 네트워크 IP 추출 중...")
        local_ip = get_local_ipv4()
        if not local_ip:
            print()
            print("  [ERROR] 네트워크 IP를 식별할 수 없습니다.")
            print("          연결 상태를 확인하세요.")
            sys.exit(1)
        config.local_ip = local_ip
        print(f"  [ OK ] 로컬 IP: {local_ip}")

        # ══════════════════════════════════════════════════════════════
        # STEP 3: 패키지 압축 해제
        # ══════════════════════════════════════════════════════════════
        print_step(3, 5, "패키지 압축 해제")
        print(f"  >> 설치 경로: {config.install_dir}")
        print(f"  >> ZIP 파일: {config.package_path.name}")
        print(f"  >> 대상 디렉터리: {config.install_dir / config.package_path.stem}")
        print()

        if not extract_package(config):
            print("  [FAIL] 패키지 압축 해제 실패")
            sys.exit(1)

        print()
        print("  prerequisite 패키지 확인")
        pkg_ok = check_packages(config)
        if not pkg_ok:
            print("  [WARN] VC++ Redistributable 설치 실패. 일부 기능이 제한될 수 있습니다.")
            if not ask_continue("패키지 문제가 있습니다. 그래도 계속 진행하시겠습니까?"):
                sys.exit(0)
        else:
            if not ask_continue("압축 해제 완료. Properties 자동 구성을 진행하시겠습니까?"):
                sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 4: sparrow.properties 자동 구성
        # ══════════════════════════════════════════════════════════════
        print_step(4, 5, "sparrow.properties 자동 구성")
        print(f"  >> 대상 파일: {config.base_dir / 'sparrow.properties'}")
        print()

        if not patch_properties(config):
            print("  [FAIL] Properties 패치 실패")
            sys.exit(1)

        if not ask_continue("Properties 구성 완료. DB 프로파일 패치를 진행하시겠습니까?"):
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 5: DB 프로파일 다국어 패치
        # ══════════════════════════════════════════════════════════════
        print_step(5, 5, "DB 프로파일 다국어 패치")

        if not patch_profiles(config, llm_client):
            print("  [WARN] 프로파일 패치에 일부 문제가 발생했습니다.")

        if not ask_continue("DB 프로파일 패치 완료. 서버 설치 및 구동을 시작하시겠습니까?"):
            sys.exit(0)

        # ══════════════════════════════════════════════════════════════
        # STEP 6: 서비스 설치 및 구동
        # ══════════════════════════════════════════════════════════════
        print_step(5, 5, "서비스 설치 및 구동")
        print(f"  >> BASE_DIR: {config.base_dir}")
        print("  >> 설치 순서: install 스크립트 → start 스크립트")
        print()

        if run_server(config, llm_client):
            print()
            modules_str = (
                ", ".join(m.upper() for m in config.enabled_optional_modules)
                if config.enabled_optional_modules else "없음"
            )
            print()
            print("=" * 70)
            print("  [ DONE ] 설치 완료")
            print("=" * 70)
            print("  Sparrow Enterprise Server 설치가 완료되었습니다!")
            print()
            print(f"  설치 경로  : {config.base_dir}")
            print(f"  접속 주소  : http://{config.local_ip}:{10880}")
            print(f"  언어 설정  : {config.language.value}")
            print(f"  활성 모듈  : {modules_str}")
            print(f"  LLM 제공자 : {llm_client.get_provider_name()}")
            print("=" * 70)
            _wait_if_exe()
        else:
            print()
            print("=" * 70)
            print("  [FAIL] 설치 실패")
            print("=" * 70)
            print("  서버 구동에 실패하였습니다.")
            print("  위의 오류 분석 리포트를 참고하여 문제를 해결하세요.")
            print("  문제 해결 후 에이전트를 다시 실행할 수 있습니다 (멱등성 지원).")
            print("=" * 70)
            _wait_if_exe()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  [WARN] 사용자에 의해 중단되었습니다.")
        _wait_if_exe()
        sys.exit(130)
    except Exception as e:
        print(f"\n  [FAIL] 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        _wait_if_exe()
        sys.exit(1)


def _wait_if_exe():
    """
    PyInstaller로 빌드된 exe 더블클릭 실행 시
    창이 즉시 닫히지 않도록 Enter 대기합니다.
    """
    if getattr(sys, "frozen", False):
        print()
        print("  계속하려면 Enter 키를 누르세요...")
        try:
            input()
        except Exception:
            pass


if __name__ == "__main__":
    main()
