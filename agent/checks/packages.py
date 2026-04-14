# -*- coding: utf-8 -*-
"""
?�수 ?�키지 ?�인
- Windows: prerequisite ?�더 ??vc_redist.x64.exe ?�인 ???�치
- Linux: unzip, fontconfig, libtinfo.so.5, libldap_r-2.4.so.2
"""
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from agent.config import (
    AgentConfig,
    LINUX_REQUIRED_PACKAGES,
    LINUX_REQUIRED_LIBS,
)

console = Console(force_terminal=True, legacy_windows=False)


def _find_vc_redist(config: AgentConfig) -> Optional[Path]:
    """
    prerequisite ?�더?�서 vc_redist.x64.exe�?먼�? 찾고,
    ?�으�?base_dir ?�체?�서 ?��? ?�색?�니??
    """
    if not config.base_dir:
        return None

    # 1?�위: prerequisite ?�더 (PRD 명세)
    prerequisite_path = config.base_dir / "prerequisite" / "vc_redist.x64.exe"
    if prerequisite_path.exists():
        return prerequisite_path

    # 2?�위: ?�체 ?��? ?�색
    for pattern in ["vc_redist.x64.exe", "vc_redist*.exe"]:
        found = list(config.base_dir.rglob(pattern))
        if found:
            return found[0]

    return None


def _check_vc_redist_installed() -> bool:
    """
    Windows ?��??�트리에??Visual C++ Redistributable ?�치 ?��?�??�인?�니??
    """
    try:
        import winreg
        keys_to_check = [
            r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
            r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\X64",
        ]
        for key_path in keys_to_check:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                installed, _ = winreg.QueryValueEx(key, "Installed")
                winreg.CloseKey(key)
                if installed == 1:
                    return True
            except (FileNotFoundError, OSError):
                continue
        return False
    except ImportError:
        return False


def _install_vc_redist(vc_redist_path: Path) -> bool:
    """vc_redist.x64.exe�??�동 ?�행?�여 ?�치?�니??"""
    console.print(
        f"  >> VC++ Redistributable ?�치 ?�작: {vc_redist_path}",
        style="cyan",
    )
    try:
        result = subprocess.run(
            [str(vc_redist_path), "/install", "/quiet", "/norestart"],
            capture_output=True,
            timeout=120,
        )
        if result.returncode in (0, 3010):  # 0=?�공, 3010=?��????�요?��?�??�공
            console.print("  [ OK ] VC++ Redistributable ?�치 ?�료", style="green")
            if result.returncode == 3010:
                console.print(
                    "  [WARN] ?��??�이 ?�요?????�습?�다. (?�치???�료??",
                    style="yellow",
                )
            return True
        else:
            console.print(
                f"  [FAIL] VC++ Redistributable ?�치 ?�패 (exit code: {result.returncode})",
                style="red",
            )
            return False
    except subprocess.TimeoutExpired:
        console.print("  [FAIL] VC++ Redistributable ?�치 ?�간 초과 (120�?", style="red")
        return False


def _check_linux_packages() -> list[str]:
    """Linux ?�수 ?�키지 �??�락????��??반환?�니??"""
    missing = []

    for pkg in LINUX_REQUIRED_PACKAGES:
        if shutil.which(pkg) is None:
            missing.append(pkg)

    try:
        result = subprocess.run(
            ["ldconfig", "-p"],
            capture_output=True, text=True, timeout=10,
        )
        for lib in LINUX_REQUIRED_LIBS:
            if lib not in result.stdout:
                missing.append(lib)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        missing.extend(LINUX_REQUIRED_LIBS)

    return missing


def check_packages(config: AgentConfig) -> bool:
    """
    OS�??�수 ?�키지 ?�치 ?��?�??�인?�니??

    Windows:
      1. prerequisite/vc_redist.x64.exe 존재 ?��? ?�인
      2. ?��? ?�치?�어 ?�으�?건너?�
      3. 미설�???prerequisite ?�더???�일�??�동 ?�치

    Returns:
        True: ?�키지 준�??�료
        False: 치명???�키지 ?�락?�로 계속 진행 불�?
    """
    if config.is_windows:
        console.print("  >> VC++ Redistributable ?�치 ?��? ?�인 �?..", style="dim")

        if _check_vc_redist_installed():
            console.print(
                "  [ OK ] VC++ Redistributable ?��? ?�치?�어 ?�습?�다.",
                style="green",
            )
            return True

        console.print(
            "  [WARN] VC++ Redistributable???�치?�어 ?��? ?�습?�다.",
            style="yellow",
        )

        # prerequisite ?�더?�서 찾기
        vc_redist_path = _find_vc_redist(config)
        if vc_redist_path:
            console.print(
                f"  >> prerequisite ?�더?�서 발견: {vc_redist_path}",
                style="cyan",
            )
            return _install_vc_redist(vc_redist_path)
        else:
            console.print(
                Panel(
                    "[bold red]prerequisite/vc_redist.x64.exe ?�일??찾을 ???�습?�다.\n"
                    "?�동?�로 ?�치 ???�시 ?�행??주세??\n"
                    "?�운로드: https://aka.ms/vs/17/release/vc_redist.x64.exe[/bold red]",
                    title="[WARN] VC++ Redistributable ?�락",
                    border_style="yellow",
                )
            )
            return False

    else:
        # Linux
        console.print("  >> Linux ?�수 ?�키지 ?�인 �?..", style="dim")
        missing = _check_linux_packages()
        if not missing:
            console.print("  [ OK ] ?�수 ?�키지 ?�치 ?�인 ?�료", style="green")
            return True
        else:
            console.print(Panel(
                "[bold red]?�음 ?�수 ?�키지가 ?�치?�어 ?��? ?�습?�다:[/bold red]\n\n"
                + "\n".join(f"  - {pkg}" for pkg in missing) + "\n\n"
                + "[dim]?�키지 매니?��??�용?�여 ?�치??주세??\n"
                + f"?? sudo apt install {' '.join(missing)}[/dim]",
                title="[WARN] ?�키지 ?�락",
                border_style="yellow",
            ))
            return False
