# -*- coding: utf-8 -*-
"""
네트워크 유틸리티
- 로컬 IPv4 주소 추출 (localhost 제외)
"""
import socket
from typing import Optional


def get_local_ipv4() -> Optional[str]:
    """
    로컬 머신의 가장 근접 가능한 IPv4 주소를 반환합니다.
    localhost(127.0.0.1)가 아닌 실제 네트워크 인터페이스 IP를 추출합니다.

    Returns:
        IPv4 주소 문자열 또는 None (추출 실패 시)
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and ip != "127.0.0.1":
                return ip
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != "127.0.0.1":
            return ip
    except socket.gaierror:
        pass

    try:
        hostname = socket.gethostname()
        addr_list = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for addr in addr_list:
            ip = addr[4][0]
            if ip != "127.0.0.1":
                return ip
    except socket.gaierror:
        pass

    return None
