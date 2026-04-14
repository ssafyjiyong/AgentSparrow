"""
자동 실행 및 로그 모니터링
- install 스크립트 실행 (실시간 출력, 에러 시 LLM 분석)
- start 스크립트 실행 (실시간 출력, 에러 시 LLM 분석, 자동 재시도)
"""
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.rule import Rule

from agent.config import AgentConfig
from agent.llm.base import LLMClient

console = Console(force_terminal=True, legacy_windows=False)

# 로그 Tail 줄 수
LOG_TAIL_LINES = 100

# ANSI 이스케이프 코드 제거 패턴
_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# 최대 재시도 횟수
MAX_RETRY = 3

# 재시도 대기 시간 (초)
RETRY_DELAY = 30


def _strip_ansi(text: str) -> str:
    """ANSI 이스케이프 코드를 제거합니다."""
    return _ANSI_ESCAPE.sub("", text)


def _find_script(base_dir: Path, name_without_ext: str, is_windows: bool) -> Optional[Path]:
    """
    base_dir 내에서 스크립트를 찾습니다.

    Args:
        base_dir: 탐색 기준 디렉터리
        name_without_ext: 스크립트 이름 (확장자 제외, 예: 'install', 'start', 'status')
        is_windows: Windows인 경우 .cmd/.bat, Linux는 .sh

    Returns:
        발견된 스크립트 Path 또는 None
    """
    if is_windows:
        candidates = [
            base_dir / f"{name_without_ext}.cmd",
            base_dir / f"{name_without_ext}.bat",
            base_dir / "bin" / f"{name_without_ext}.cmd",
            base_dir / "bin" / f"{name_without_ext}.bat",
        ]
    else:
        candidates = [
            base_dir / f"{name_without_ext}.sh",
            base_dir / "bin" / f"{name_without_ext}.sh",
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # 패턴 기반 검색 (1단계 하위)
    exts = [".cmd", ".bat"] if is_windows else [".sh"]
    for ext in exts:
        for script in base_dir.glob(f"*{ext}"):
            if name_without_ext in script.name.lower():
                return script

    return None


def _stream_process(args: list, cwd: str) -> int:
    """
    subprocess를 실행하고 stdout/stderr를 실시간으로 콘솔에 출력합니다.
    ANSI 이스케이프 코드를 자동으로 제거하여 깔끔하게 출력합니다.

    Args:
        args: 실행 명령어 리스트
        cwd: 작업 디렉터리

    Returns:
        프로세스 종료 코드
    """
    console.print(f"  [dim]실행: {' '.join(str(a) for a in args)}[/dim]")
    console.print()

    try:
        process = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in iter(process.stdout.readline, ""):
            line = _strip_ansi(line.rstrip())
            if not line.strip():
                continue
            safe = escape(line)
            # ERROR / FATAL / Exception → 빨간색
            if any(kw in line for kw in ("ERROR", "FATAL", "Exception", "FAIL")):
                console.print(f"  [red]{safe}[/red]")
            # WARN → 노란색
            elif "WARN" in line:
                console.print(f"  [yellow]{safe}[/yellow]")
            # 일반 → 흐리게
            else:
                console.print(f"  [dim]{safe}[/dim]")

        process.stdout.close()
        return_code = process.wait()
        return return_code

    except FileNotFoundError:
        console.print(f"  [bold red][FAIL] 실행 파일을 찾을 수 없습니다: {args[0]}[/bold red]")
        return 1
    except Exception as e:
        console.print(f"  [bold red][FAIL] 실행 오류: {e}[/bold red]")
        return 1


def _collect_log_tail(config: AgentConfig, lines: int = LOG_TAIL_LINES) -> str:
    """
    로그 파일에서 마지막 N줄을 수집합니다.
    모니터링 대상: ops/logs, logs/[모듈명]
    """
    log_dirs = []
    if config.base_dir:
        log_dirs.extend([
            config.base_dir / "ops" / "logs",
            config.base_dir / "logs",
        ])

    collected_logs = []

    for log_dir in log_dirs:
        if not log_dir.exists():
            continue
        for log_file in log_dir.rglob("*.log"):
            try:
                content = log_file.read_text(encoding="utf-8", errors="replace")
                file_lines = content.splitlines()
                tail = file_lines[-lines:] if len(file_lines) > lines else file_lines

                error_lines = [
                    l for l in tail
                    if "ERROR" in l or "FATAL" in l or "Exception" in l
                ]

                if error_lines:
                    collected_logs.append(
                        f"\n=== {log_file.relative_to(config.base_dir)} ===\n"
                        + "\n".join(error_lines[-30:])
                    )
            except Exception:
                continue

    if not collected_logs:
        # 에러가 없으면 최근 로그 파일의 마지막 N줄을 반환
        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
            log_files = sorted(
                log_dir.rglob("*.log"),
                key=lambda p: p.stat().st_mtime if p.exists() else 0,
                reverse=True,
            )
            if log_files:
                try:
                    content = log_files[0].read_text(encoding="utf-8", errors="replace")
                    file_lines = content.splitlines()
                    tail = file_lines[-lines:]
                    return f"=== {log_files[0].name} (최근 {len(tail)}줄) ===\n" + "\n".join(tail)
                except Exception:
                    pass

    return "\n".join(collected_logs) if collected_logs else "수집된 로그가 없습니다."


def _analyze_failure(config: AgentConfig, llm_client: LLMClient, context: str):
    """실패 시 LLM을 사용하여 로그를 분석합니다."""
    console.print()
    console.print("  [bold yellow][LLM] 오류 로그를 분석합니다...[/bold yellow]")

    log_content = _collect_log_tail(config)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("[SCAN] 로그 분석 중...", total=None)
            analysis = llm_client.analyze_log(log_content, context)

        console.print()
        console.print(Panel(
            Markdown(analysis),
            title="[bold yellow][SCAN] 오류 분석 리포트[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        ))
    except Exception as e:
        console.print(f"  [bold yellow][WARN] LLM 분석 실패: {e}[/bold yellow]")
        console.print()
        # LLM 실패 시 로그 원문을 패널로 출력
        log_excerpt = log_content[:3000] if log_content else "로그 없음"
        console.print(Panel(
            escape(log_excerpt),
            title="[dim]최근 서버 로그[/dim]",
            border_style="dim",
        ))


def _check_via_status(config: AgentConfig) -> bool:
    """
    status 스크립트를 실행하여 서버 모듈 구동 여부를 확인합니다.
    (pid XXXXX) 패턴이 5개 이상 발견되면 서버가 정상 구동 중으로 판단합니다.

    Returns:
        True: 서버 정상 구동 중
        False: 서버 미구동 또는 확인 불가
    """
    status_script = _find_script(config.base_dir, "status", config.is_windows)
    if not status_script:
        return False

    if config.is_windows:
        args = ["cmd", "/c", str(status_script)]
    else:
        args = ["bash", str(status_script)]

    try:
        result = subprocess.run(
            args,
            cwd=str(status_script.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        output = _strip_ansi(result.stdout + result.stderr)
        # (pid XXXXX) 패턴으로 구동 중인 모듈 수 계산
        started = len(re.findall(r"\(pid\s+\d+\)", output))
        return started >= 5
    except Exception:
        return False


def run_server(config: AgentConfig, llm_client: LLMClient) -> bool:
    """
    설치 → 구동 순서로 Sparrow를 설치합니다.

    순서:
      1. install 스크립트 실행 (실시간 출력, 실패 시 LLM 분석)
      2. start 스크립트 실행 → status 스크립트로 실제 구동 확인
         실패 시 LLM 분석 후 최대 MAX_RETRY 회 자동 재시도

    Args:
        config: 에이전트 설정
        llm_client: LLM 클라이언트

    Returns:
        True: 서버 정상 구동
        False: 실패
    """
    if not config.base_dir or not config.base_dir.exists():
        console.print("  [bold red][FAIL] BASE_DIR이 설정되지 않았습니다.[/bold red]")
        return False

    # ── PHASE 1: install 스크립트 실행 ────────────────────────────────
    console.print(Rule("[bold]PHASE 1: 설치 (install)[/bold]", style="bright_blue"))
    console.print()

    install_script = _find_script(config.base_dir, "install", config.is_windows)
    if not install_script:
        console.print(
            "  [bold red][FAIL] install 스크립트를 찾을 수 없습니다."
            " (install.cmd / install.sh 탐색 실패)[/bold red]",
        )
        return False

    console.print(f"  [cyan]>> install 스크립트: {install_script}[/cyan]")

    if config.is_windows:
        install_args = ["cmd", "/c", str(install_script)]
    else:
        install_script.chmod(0o755)
        install_args = ["bash", str(install_script)]

    install_rc = _stream_process(
        args=install_args,
        cwd=str(install_script.parent),
    )

    if install_rc != 0:
        console.print(
            f"\n  [bold red][FAIL] install 스크립트 실패 (exit code: {install_rc})[/bold red]",
        )
        _analyze_failure(config, llm_client, f"install 스크립트 비정상 종료 (exit code: {install_rc})")
        return False

    console.print(
        f"\n  [bold green][ OK ] install 완료 (exit code: {install_rc})[/bold green]",
    )
    console.print()

    # ── PHASE 2: start 스크립트 실행 (자동 재시도 포함) ─────────────
    start_script = _find_script(config.base_dir, "start", config.is_windows)
    if not start_script:
        console.print(
            "  [bold red][FAIL] start 스크립트를 찾을 수 없습니다."
            " (start.cmd / start.sh 탐색 실패)[/bold red]",
        )
        return False

    if config.is_windows:
        start_args = ["cmd", "/c", str(start_script)]
    else:
        start_script.chmod(0o755)
        start_args = ["bash", str(start_script)]

    for attempt in range(1, MAX_RETRY + 1):
        if attempt == 1:
            console.print(Rule("[bold]PHASE 2: 서버 구동 (start)[/bold]", style="bright_blue"))
        else:
            console.print(Rule(
                f"[bold]PHASE 2: 서버 구동 재시도 [{attempt}/{MAX_RETRY}][/bold]",
                style="yellow",
            ))
        console.print()

        console.print(f"  [cyan]>> start 스크립트: {start_script}[/cyan]")
        console.print()

        _stream_process(
            args=start_args,
            cwd=str(start_script.parent),
        )

        # start 스크립트 종료 후 status 스크립트로 실제 구동 여부 확인
        console.print()
        console.print("  [dim]>> 서버 구동 상태 확인 중...[/dim]")

        if _check_via_status(config):
            console.print(
                "  [bold green][ OK ] 서버 구동 확인 완료[/bold green]",
            )
            return True

        # 서버가 실제로 구동되지 않은 경우
        console.print(
            f"  [bold red][FAIL] 서버 구동 확인 실패 (시도 {attempt}/{MAX_RETRY})[/bold red]",
        )

        if attempt < MAX_RETRY:
            _analyze_failure(
                config,
                llm_client,
                f"서버 구동 실패 (시도 {attempt}/{MAX_RETRY})",
            )
            console.print()
            console.print(f"  [yellow]>> {RETRY_DELAY}초 후 재시도합니다...[/yellow]")
            time.sleep(RETRY_DELAY)
        else:
            _analyze_failure(
                config,
                llm_client,
                f"서버 구동 최종 실패 ({MAX_RETRY}회 시도 모두 실패)",
            )

    return False
