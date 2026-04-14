# -*- coding: utf-8 -*-
"""
포트 충돌 검사
- 필수 포트를 스캔하여 사용 중인 포트를 식별
"""
import socket

from agent.config import REQUIRED_PORTS


def _is_port_in_use(port: int, host: str = "localhost") -> bool:
    """지정 포트가 사용 중인지 확인합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0


def check_ports() -> bool:
    """
    필수 포트의 사용 여부를 검사합니다.
    사용 중인 포트가 있으면 False를 반환합니다.

    Returns:
        True: 모든 포트가 사용 가능
        False: 하나 이상의 포트가 사용 중
    """
    occupied_ports = []

    for port in REQUIRED_PORTS:
        if _is_port_in_use(port):
            occupied_ports.append(port)

    if occupied_ports:
        print()
        print("  [WARN] 포트 충돌 감지")
        print("  " + "-" * 40)
        for port in occupied_ports:
            print(f"  [X] 포트 {port} - 사용 중")
        print("  " + "-" * 40)
        print()
        for port in occupied_ports:
            print(f"  [ERROR] 포트 {port}가 이미 사용 중입니다.")
            print(f"         점유 중인 프로세스를 종료하세요.")
        print()
        return False

    print(f"  [ OK ] 포트 충돌 검사 완료 ({len(REQUIRED_PORTS)}개 포트 모두 사용 가능)")
    return True
