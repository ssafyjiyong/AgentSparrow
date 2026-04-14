# -*- coding: utf-8 -*-
"""
?�트?�크 ?�틸리티
- 로컬 IPv4 주소 추출 (localhost ?�외)
"""
import socket
from typing import Optional

from rich.console import Console

console = Console(force_terminal=True, legacy_windows=False)


def get_local_ipv4() -> Optional[str]:
    """
    로컬 머신???��? ?�근 가?�한 IPv4 주소�?반환?�니??
    localhost(127.0.0.1)가 ?�닌 ?�제 ?�트?�크 ?�터?�이??IP�?추출?�니??

    Returns:
        IPv4 주소 문자???�는 None (추출 ?�패 ??
    """
    try:
        # UDP ?�켓???�용?�여 ?��? ?�결 ?��??�이??(?�제 ?�결?� ?��? ?�음)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and ip != "127.0.0.1":
                return ip
    except OSError:
        pass

    # ?�백: hostname 기반 조회
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != "127.0.0.1":
            return ip
    except socket.gaierror:
        pass

    # 모든 주소 ?�회
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
