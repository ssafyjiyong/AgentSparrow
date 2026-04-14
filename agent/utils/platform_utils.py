"""
플랫폼 유틸리티
- OS 판별, 경로 정규화, 관리자 권한 확인
"""
import ctypes
import os
import platform
from pathlib import Path

from agent.config import OSType


def detect_os() -> OSType:
    """현재 OS 타입을 감지합니다."""
    system = platform.system()
    if system == "Windows":
        return OSType.WINDOWS
    return OSType.LINUX


def is_admin() -> bool:
    """
    현재 프로세스가 관리자/root 권한으로 실행 중인지 확인합니다.

    Returns:
        True이면 관리자/root 권한
    """
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except (AttributeError, OSError):
            return False
    else:
        return os.geteuid() == 0


def normalize_path(path_str: str) -> Path:
    """경로 문자열을 정규화된 Path 객체로 변환합니다."""
    return Path(path_str).resolve()


def ensure_dir(path: Path) -> Path:
    """디렉토리가 존재하지 않으면 생성합니다."""
    path.mkdir(parents=True, exist_ok=True)
    return path
