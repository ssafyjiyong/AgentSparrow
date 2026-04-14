# -*- coding: utf-8 -*-
"""
실행 권한 검증
- Windows: 관리자 권한이면 오류 (PostgreSQL 제약)
- Linux: root이면 오류
"""
import sys

from agent.config import AgentConfig
from agent.utils.platform_utils import is_admin


def check_permissions(config: AgentConfig) -> bool:
    """
    실행 권한을 검증합니다.
    관리자/root 권한이면 False를 반환하고 오류 메시지를 출력합니다.

    Returns:
        True: 권한이 적절함 (일반 사용자)
        False: 관리자/root로 실행됨 (중단 필요)
    """
    if is_admin():
        print()
        print("  [ERROR] 권한 오류")
        print("  " + "=" * 50)
        if config.is_windows:
            print("  PostgreSQL 제약으로 인해 일반 사용자 권한으로")
            print("  에이전트를 다시 실행해 주세요.")
            print()
            print("  현재 관리자(Admin) 권한으로 실행 중입니다.")
            print("  Windows Terminal 또는 CMD를 일반 사용자 모드로")
            print("  열고 다시 시도해 주세요.")
        else:
            print("  PostgreSQL 제약으로 인해 일반 사용자 권한으로 실행해 주세요.")
            print()
            print("  현재 root 계정으로 실행 중입니다.")
            print("  일반 사용자 계정으로 전환 후 다시 시도해 주세요.")
            print("  예) su - sparrow && ./sparrow-agent")
        print("  " + "=" * 50)
        print()
        return False

    print("  [ OK ] 실행 권한 확인 완료 (일반 사용자)")
    return True
