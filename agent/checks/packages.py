# -*- coding: utf-8 -*-
"""
필수 패키지 확인
- Windows: prerequisite 폴더 내 vc_redist.x64.exe 확인 및 설치
- Linux: unzip, fontconfig, libtinfo.so.5, libldap_r-2.4.so.2
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from agent.config import (
    AgentConfig,
    LINUX_REQUIRED_PACKAGES,
    LINUX_REQUIRED_LIBS,
)


def _find_vc_redist(config: AgentConfig) -> Optional[Path]:
    if not config.base_dir:
        return None

    prerequisite_path = config.base_dir / "prerequisite" / "vc_redist.x64.exe"
    if prerequisite_path.exists():
        return prerequisite_path

    for pattern in ["vc_redist.x64.exe", "vc_redist*.exe"]:
        found = list(config.base_dir.rglob(pattern))
        if found:
            return found[0]

    return None


def _check_vc_redist_installed() -> bool:
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
    print(f"  >> VC++ Redistributable 설치 시작: {vc_redist_path}")
    try:
        result = subprocess.run(
            [str(vc_redist_path), "/install", "/quiet", "/norestart"],
            capture_output=True,
            timeout=120,
        )
        if result.returncode in (0, 3010):
            print("  [ OK ] VC++ Redistributable 설치 완료")
            if result.returncode == 3010:
                print("  [WARN] 재부팅이 필요할 수 있습니다. (설치는 완료됨)")
            return True
        else:
            print(f"  [FAIL] VC++ Redistributable 설치 실패 (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print("  [FAIL] VC++ Redistributable 설치 시간 초과 (120초)")
        return False


def _check_linux_packages() -> list[str]:
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
    OS별 필수 패키지 설치 여부를 확인합니다.

    Returns:
        True: 패키지 준비 완료
        False: 치명적 패키지 누락으로 계속 진행 불가
    """
    if config.is_windows:
        print("  >> VC++ Redistributable 설치 여부 확인 중...")

        if _check_vc_redist_installed():
            print("  [ OK ] VC++ Redistributable 이미 설치되어 있습니다.")
            return True

        print("  [WARN] VC++ Redistributable이 설치되어 있지 않습니다.")

        vc_redist_path = _find_vc_redist(config)
        if vc_redist_path:
            print(f"  >> prerequisite 폴더에서 발견: {vc_redist_path}")
            return _install_vc_redist(vc_redist_path)
        else:
            print()
            print("  [WARN] VC++ Redistributable 누락")
            print("  " + "-" * 50)
            print("  prerequisite/vc_redist.x64.exe 파일을 찾을 수 없습니다.")
            print("  수동으로 설치 후 다시 실행해 주세요.")
            print("  다운로드: https://aka.ms/vs/17/release/vc_redist.x64.exe")
            print("  " + "-" * 50)
            print()
            return False

    else:
        print("  >> Linux 필수 패키지 확인 중...")
        missing = _check_linux_packages()
        if not missing:
            print("  [ OK ] 필수 패키지 설치 확인 완료")
            return True
        else:
            print()
            print("  [WARN] 패키지 누락")
            print("  " + "-" * 50)
            print("  다음 필수 패키지가 설치되어 있지 않습니다:")
            for pkg in missing:
                print(f"    - {pkg}")
            print()
            print(f"  예) sudo apt install {' '.join(missing)}")
            print("  " + "-" * 50)
            print()
            return False
