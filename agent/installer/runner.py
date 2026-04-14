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

from agent.config import AgentConfig
from agent.llm.base import LLMClient

# 로그 Tail 줄 수
LOG_TAIL_LINES = 100

# ANSI 이스케이프 코드 제거 패턴
_ANSI_ESCAPE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
    r"|\[[\d;]*[A-Za-z]"
)

# 최대 재시도 횟수
MAX_RETRY = 3

# 재시도 대기 시간 (초)
RETRY_DELAY = 30


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _print_section(title: str, char: str = "="):
    width = 60
    line = char * width
    print()
    print(line)
    print(f"  {title}")
    print(line)


def _find_script(base_dir: Path, name_without_ext: str, is_windows: bool) -> Optional[Path]:
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

    exts = [".cmd", ".bat"] if is_windows else [".sh"]
    for ext in exts:
        for script in base_dir.glob(f"*{ext}"):
            if name_without_ext in script.name.lower():
                return script

    return None


def _stream_process(args: list, cwd: str) -> int:
    """
    subprocess를 실행하고 stdout/stderr를 실시간으로 출력합니다.
    ANSI 이스케이프 코드를 자동으로 제거합니다.
    """
    print(f"  실행: {' '.join(str(a) for a in args)}")
    print()

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
            if any(kw in line for kw in ("ERROR", "FATAL", "Exception", "FAIL")):
                print(f"  [ERROR] {line}")
            elif "WARN" in line:
                print(f"  [WARN]  {line}")
            else:
                print(f"  {line}")

        process.stdout.close()
        return process.wait()

    except FileNotFoundError:
        print(f"  [FAIL] 실행 파일을 찾을 수 없습니다: {args[0]}")
        return 1
    except Exception as e:
        print(f"  [FAIL] 실행 오류: {e}")
        return 1


def _collect_log_tail(config: AgentConfig, lines: int = LOG_TAIL_LINES) -> str:
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
    print()
    print("  [LLM] 오류 로그를 분석합니다...")

    log_content = _collect_log_tail(config)

    try:
        print("  [SCAN] 로그 분석 중...")
        analysis = llm_client.analyze_log(log_content, context)
        print()
        print("  " + "=" * 60)
        print("  [SCAN] 오류 분석 리포트")
        print("  " + "=" * 60)
        for line in analysis.splitlines():
            print(f"  {line}")
        print("  " + "=" * 60)
    except Exception as e:
        print(f"  [WARN] LLM 분석 실패: {e}")
        print()
        print("  최근 서버 로그:")
        print("  " + "-" * 60)
        excerpt = log_content[:3000] if log_content else "로그 없음"
        for line in excerpt.splitlines():
            print(f"  {line}")
        print("  " + "-" * 60)


def _check_via_status(config: AgentConfig) -> bool:
    """
    status 스크립트를 실행하여 서버 모듈 구동 여부를 확인합니다.
    (pid XXXXX) 패턴이 5개 이상 발견되면 서버가 정상 구동 중으로 판단합니다.
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
        started = len(re.findall(r"\(pid\s+\d+\)", output))
        return started >= 5
    except Exception:
        return False


def run_server(config: AgentConfig, llm_client: LLMClient) -> bool:
    """
    설치 → 구동 순서로 Sparrow를 설치합니다.

    Returns:
        True: 서버 정상 구동
        False: 실패
    """
    if not config.base_dir or not config.base_dir.exists():
        print("  [FAIL] BASE_DIR이 설정되지 않았습니다.")
        return False

    # ── PHASE 1: install 스크립트 실행 ────────────────────────────────
    _print_section("PHASE 1: 설치 (install)")

    install_script = _find_script(config.base_dir, "install", config.is_windows)
    if not install_script:
        print("  [FAIL] install 스크립트를 찾을 수 없습니다. (install.cmd / install.sh 탐색 실패)")
        return False

    print(f"  >> install 스크립트: {install_script}")

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
        print(f"\n  [FAIL] install 스크립트 실패 (exit code: {install_rc})")
        _analyze_failure(config, llm_client, f"install 스크립트 비정상 종료 (exit code: {install_rc})")
        return False

    print(f"\n  [ OK ] install 완료 (exit code: {install_rc})")

    # ── PHASE 2: start 스크립트 실행 (자동 재시도 포함) ─────────────
    start_script = _find_script(config.base_dir, "start", config.is_windows)
    if not start_script:
        print("  [FAIL] start 스크립트를 찾을 수 없습니다. (start.cmd / start.sh 탐색 실패)")
        return False

    if config.is_windows:
        start_args = ["cmd", "/c", str(start_script)]
    else:
        start_script.chmod(0o755)
        start_args = ["bash", str(start_script)]

    for attempt in range(1, MAX_RETRY + 1):
        if attempt == 1:
            _print_section("PHASE 2: 서버 구동 (start)")
        else:
            _print_section(f"PHASE 2: 서버 구동 재시도 [{attempt}/{MAX_RETRY}]", char="-")

        print(f"  >> start 스크립트: {start_script}")
        print()

        _stream_process(
            args=start_args,
            cwd=str(start_script.parent),
        )

        print()
        print("  >> 서버 구동 상태 확인 중...")

        if _check_via_status(config):
            print("  [ OK ] 서버 구동 확인 완료")
            return True

        print(f"  [FAIL] 서버 구동 확인 실패 (시도 {attempt}/{MAX_RETRY})")

        if attempt < MAX_RETRY:
            _analyze_failure(
                config,
                llm_client,
                f"서버 구동 실패 (시도 {attempt}/{MAX_RETRY})",
            )
            print()
            print(f"  >> {RETRY_DELAY}초 후 재시도합니다...")
            time.sleep(RETRY_DELAY)
        else:
            _analyze_failure(
                config,
                llm_client,
                f"서버 구동 최종 실패 ({MAX_RETRY}회 시도 모두 실패)",
            )

    return False
