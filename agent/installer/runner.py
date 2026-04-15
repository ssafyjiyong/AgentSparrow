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
from agent.cli import ensure_llm_client

# Sparrow 구동 모듈 목록 (logs/<module>/ 하위에서 로그 탐색)
RUNTIME_MODULES = [
    "backend", "dast", "db", "frontend", "gateway",
    "plugin", "sast", "sca", "update",
]

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


def _tail_log_file(log_file: Path, lines: int, base_dir: Path) -> Optional[str]:
    """단일 로그 파일을 tail 하고, 오류 라인이 있으면 그것만, 아니면 일반 tail을 반환."""
    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    file_lines = content.splitlines()
    tail = file_lines[-lines:] if len(file_lines) > lines else file_lines

    error_lines = [
        l for l in tail
        if "ERROR" in l or "FATAL" in l or "Exception" in l
    ]

    try:
        rel = log_file.relative_to(base_dir)
    except ValueError:
        rel = log_file

    if error_lines:
        return f"\n=== {rel} ===\n" + "\n".join(error_lines[-30:])
    if tail:
        return f"\n=== {rel} (최근 {len(tail)}줄) ===\n" + "\n".join(tail)
    return None


def _collect_install_logs(config: AgentConfig, lines: int = LOG_TAIL_LINES) -> str:
    """
    설치 실패 시: base_dir/ops/logs 하위의 로그를 수집합니다.
    (예: C:/Sparrow/sparrow-enterprise-server-windows-2603.2/ops/logs)
    """
    if not config.base_dir:
        return "BASE_DIR이 설정되지 않아 로그를 수집할 수 없습니다."

    log_dir = config.base_dir / "ops" / "logs"
    if not log_dir.exists():
        return f"설치 로그 디렉터리가 존재하지 않습니다: {log_dir}"

    collected = []
    for log_file in sorted(
        log_dir.rglob("*.log"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    ):
        chunk = _tail_log_file(log_file, lines, config.base_dir)
        if chunk:
            collected.append(chunk)

    return "\n".join(collected) if collected else "수집된 설치 로그가 없습니다."


def _collect_runtime_logs(
    config: AgentConfig,
    failed_modules: Optional[list] = None,
    lines: int = LOG_TAIL_LINES,
) -> str:
    """
    구동 실패 시: base_dir/logs/<module>/*.log 에서 구동 실패한 모듈의 로그 수집.
    failed_modules가 비어 있으면 구동 모듈 전체를 스캔합니다.
    """
    if not config.base_dir:
        return "BASE_DIR이 설정되지 않아 로그를 수집할 수 없습니다."

    log_root = config.base_dir / "logs"
    if not log_root.exists():
        return f"구동 로그 디렉터리가 존재하지 않습니다: {log_root}"

    modules_to_scan = failed_modules if failed_modules else RUNTIME_MODULES
    collected = []

    for module in modules_to_scan:
        module_dir = log_root / module
        if not module_dir.exists():
            continue
        # 모듈별로 최근 수정된 로그 파일 우선 순회
        log_files = sorted(
            module_dir.rglob("*.log"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        for log_file in log_files[:3]:  # 모듈당 최근 3개까지
            chunk = _tail_log_file(log_file, lines, config.base_dir)
            if chunk:
                collected.append(chunk)

    if not collected:
        header = (
            f"대상 모듈: {', '.join(modules_to_scan)}\n"
            if modules_to_scan else ""
        )
        return header + "수집된 구동 로그가 없습니다."
    return "\n".join(collected)


def _analyze_failure(
    config: AgentConfig,
    context: str,
    phase: str,
    failed_modules: Optional[list] = None,
):
    """
    실패 시 로그를 수집하고, (필요 시 지연 초기화된) LLM으로 분석합니다.

    phase:
        "install" - 설치 실패. ops/logs 수집.
        "runtime" - 구동 실패. logs/<module> 수집.
    """
    print()
    if phase == "install":
        print("  [LOG] 설치 로그 수집: ops/logs")
        log_content = _collect_install_logs(config)
    else:
        modules_str = (
            ", ".join(failed_modules) if failed_modules else "(전체 구동 모듈)"
        )
        print(f"  [LOG] 구동 로그 수집: logs/{{{modules_str}}}")
        log_content = _collect_runtime_logs(config, failed_modules)

    reason = "설치 실패 로그 분석" if phase == "install" else "구동 실패 로그 분석"
    llm_client = ensure_llm_client(config, reason=reason)

    if llm_client is None:
        print()
        print("  [WARN] LLM 클라이언트가 없어 원시 로그만 출력합니다.")
        print("  " + "-" * 60)
        excerpt = log_content[:5000] if log_content else "로그 없음"
        for line in excerpt.splitlines():
            print(f"  {line}")
        print("  " + "-" * 60)
        return

    try:
        print("  [SCAN] LLM 로그 분석 중...")
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


def _run_status_script(config: AgentConfig) -> str:
    """status 스크립트 실행 후 출력(stdout+stderr)을 반환. 실패 시 빈 문자열."""
    status_script = _find_script(config.base_dir, "status", config.is_windows)
    if not status_script:
        return ""

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
        return _strip_ansi(result.stdout + result.stderr)
    except Exception:
        return ""


def _check_via_status(config: AgentConfig) -> bool:
    """(pid XXXXX) 패턴이 5개 이상이면 정상 구동으로 판단."""
    output = _run_status_script(config)
    if not output:
        return False
    started = len(re.findall(r"\(pid\s+\d+\)", output))
    return started >= 5


def _detect_failed_modules(config: AgentConfig) -> list:
    """
    status 스크립트 출력에서 구동 실패한 모듈을 추정합니다.
    각 라인에 모듈명이 등장하는데 (pid XXXXX) 가 붙어 있지 않으면 실패로 간주합니다.
    탐지에 실패하면 빈 리스트 반환 → 전체 모듈을 스캔합니다.
    """
    output = _run_status_script(config)
    if not output:
        return []

    failed = []
    for line in output.splitlines():
        low = line.lower()
        for module in RUNTIME_MODULES:
            if module in low and not re.search(r"\(pid\s+\d+\)", line):
                if module not in failed:
                    failed.append(module)
    return failed


def run_server(config: AgentConfig) -> bool:
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
        _analyze_failure(
            config,
            context=f"install 스크립트 비정상 종료 (exit code: {install_rc})",
            phase="install",
        )
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

        failed_modules = _detect_failed_modules(config)
        if failed_modules:
            print(f"  [DETECT] 실패 모듈: {', '.join(failed_modules)}")

        if attempt < MAX_RETRY:
            _analyze_failure(
                config,
                context=f"서버 구동 실패 (시도 {attempt}/{MAX_RETRY})",
                phase="runtime",
                failed_modules=failed_modules,
            )
            print()
            print(f"  >> {RETRY_DELAY}초 후 재시도합니다...")
            time.sleep(RETRY_DELAY)
        else:
            _analyze_failure(
                config,
                context=f"서버 구동 최종 실패 ({MAX_RETRY}회 시도 모두 실패)",
                phase="runtime",
                failed_modules=failed_modules,
            )

    return False
