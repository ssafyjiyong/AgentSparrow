# -*- coding: utf-8 -*-
"""
?�트 충돌 검??
- ?��? ?�???�트�??�캔?�여 ?�용 중인 ?�트�??�별
"""
import socket

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.config import REQUIRED_PORTS

console = Console(force_terminal=True, legacy_windows=False)


def _is_port_in_use(port: int, host: str = "localhost") -> bool:
    """?�정 ?�트가 ?�용 중인지 ?�인?�니??"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0


def check_ports() -> bool:
    """
    ?�수 ?�트???�용 ?��?�?검?�합?�다.
    ?�용 중인 ?�트가 ?�으�?False�?반환?�니??

    Returns:
        True: 모든 ?�트가 ?�용 가??
        False: ?�나 ?�상???�트가 ?�용 �?
    """
    occupied_ports = []

    for port in REQUIRED_PORTS:
        if _is_port_in_use(port):
            occupied_ports.append(port)

    if occupied_ports:
        # ?�트 충돌 ?�이�?출력
        table = Table(
            title="[WARN] ?�트 충돌 감�?",
            show_header=True,
            header_style="bold red",
        )
        table.add_column("?�트", style="cyan", justify="center")
        table.add_column("?�태", style="red", justify="center")

        for port in occupied_ports:
            table.add_row(str(port), "[X] ?�용 �?)

        console.print(table)
        console.print()

        for port in occupied_ports:
            console.print(Panel(
                f"[bold red][ERROR] ?�트 {port}가 ?��? ?�용 중입?�다. "
                f"?�유 중인 ?�로?�스�?종료?�세??[/bold red]",
                border_style="red",
            ))

        return False

    console.print(
        f"  [ OK ] ?�트 충돌 검???�료 ({len(REQUIRED_PORTS)}�??�트 모두 ?�용 가??",
        style="green",
    )
    return True
