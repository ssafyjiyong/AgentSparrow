# -*- coding: utf-8 -*-
"""
?�행 권한 검�?
- Windows: 관리자 권한?�면 ?�러 (PostgreSQL ?�약)
- Linux: root?�면 ?�러
"""
import sys

from rich.console import Console
from rich.panel import Panel

from agent.config import AgentConfig
from agent.utils.platform_utils import is_admin

console = Console(force_terminal=True, legacy_windows=False)


def check_permissions(config: AgentConfig) -> bool:
    """
    ?�행 권한??검증합?�다.
    관리자/root 권한?�면 False�?반환?�고 ?�러 메시지�?출력?�니??

    PRD ?�구?�항:
    - Windows: Admin 권한 ???�반 ?�용?�로 ?�실?�하?�록 ?�내
    - Linux: root ???�반 ?�용??권한 ?�구

    Args:
        config: ?�이?�트 ?�정

    Returns:
        True: 권한???�절??(?�반 ?�용??
        False: 관리자/root�??�행??(중단 ?�요)
    """
    if is_admin():
        if config.is_windows:
            console.print(Panel(
                "[bold red][ERROR] PostgreSQL ?�약?�로 ?�해 "
                "?�반 ?�용??권한?�로 ?��??�을 ?�시 ?�행??주세??[/bold red]\n\n"
                "[dim]?�재 관리자(Admin) 권한?�로 ?�행 중입?�다.\n"
                "Windows Terminal ?�는 CMD�??�반 ?�용??모드�??�고 ?�시 ?�도??주세??[/dim]",
                title="[ERR] 권한 ?�류",
                border_style="red",
            ))
        else:
            console.print(Panel(
                "[bold red][ERROR] PostgreSQL ?�약?�로 ?�해 "
                "?�반 ?�용??권한?�로 ?�행??주세??[/bold red]\n\n"
                "[dim]?�재 root 계정?�로 ?�행 중입?�다.\n"
                "?�반 ?�용??계정?�로 ?�환 ???�시 ?�도??주세??\n"
                "?? su - sparrow && ./sparrow-agent[/dim]",
                title="[ERR] 권한 ?�류",
                border_style="red",
            ))
        return False

    console.print("  [ OK ] ?�행 권한 ?�인 ?�료 (?�반 ?�용??", style="green")
    return True
