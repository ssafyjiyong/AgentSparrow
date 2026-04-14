# -*- coding: utf-8 -*-
"""
포트 충돌 검사
- 필수 포트를 병렬로 스캔하여 사용 중인 포트를 식별
- ThreadPoolExecutor 로 동시에 검사하여 속도 대폭 개선
"""
import io
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent.config import REQUIRED_PORTS

# Windows 터미널에서 utf-8 출력 강제 (cp949 인코딩 오류 방지)
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    except AttributeError:
        pass  # frozen exe 등 buffer가 없는 경우 무시


def _is_port_in_use(port: int, host: str = "localhost", timeout: float = 0.5) -> bool:
    """지정 포트가 사용 중인지 확인합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result == 0


def check_ports() -> bool:
    """
    필수 포트의 사용 여부를 병렬로 검사합니다.
    사용 중인 포트가 있으면 False를 반환합니다.

    Returns:
        True: 모든 포트가 사용 가능
        False: 하나 이상의 포트가 사용 중
    """
    total = len(REQUIRED_PORTS)
    occupied_ports = []
    checked = [0]
    lock = threading.Lock()

    # ── 진행 표시 (같은 줄에서 갱신, ASCII 문자 사용으로 인코딩 호환) ──
    def _print_progress(current: int, total: int):
        bar_width = 30
        filled = int(bar_width * current / total)
        bar = "#" * filled + "-" * (bar_width - filled)
        sys.stdout.write(f"\r  확인중 ... [{bar}] {current}/{total} 포트")
        sys.stdout.flush()

    _print_progress(0, total)

    def _check(port: int):
        in_use = _is_port_in_use(port)
        with lock:
            checked[0] += 1
            _print_progress(checked[0], total)
            if in_use:
                occupied_ports.append(port)

    # 최대 16 스레드로 병렬 검사
    with ThreadPoolExecutor(max_workers=min(16, total)) as executor:
        futures = [executor.submit(_check, p) for p in REQUIRED_PORTS]
        for _ in as_completed(futures):
            pass

    # 진행 바 줄바꿈
    print()

    if occupied_ports:
        print()
        print("  [WARN] 포트 충돌 감지")
        print("  " + "-" * 40)
        for port in sorted(occupied_ports):
            print(f"  [X] 포트 {port} - 사용 중")
        print("  " + "-" * 40)
        print()
        for port in sorted(occupied_ports):
            print(f"  [ERROR] 포트 {port}가 이미 사용 중입니다.")
            print(f"         점유 중인 프로세스를 종료하세요.")
        print()
        return False

    print(f"  [ OK ] 포트 충돌 검사 완료 ({total}개 포트 모두 사용 가능)")
    return True
