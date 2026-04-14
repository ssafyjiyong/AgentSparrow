# -*- coding: utf-8 -*-
"""
?�키지 ?�축 ?�제 �?경로 최적??- ZIP ?�일 ?�름�??�일???�렉?�리�?install_dir ?�래???�성
- �??�에 ?�축 ?�제
- BASE_DIR ?�경 변??매핑
"""
import os
import re
import zipfile
from pathlib import Path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from agent.config import AgentConfig, VERSION_PATTERN
from agent.utils.platform_utils import ensure_dir

console = Console(force_terminal=True, legacy_windows=False)


def extract_package(config: AgentConfig) -> bool:
    """
    Sparrow Enterprise Server ?�키지�??�축 ?�제?�니??

    규칙:
    - ZIP ?�일�??�장???�외)�??�일???�름???�렉?�리�?install_dir ?�래???�성
    - �??�렉?�리 ?�에 ?�축 ?�제
    - BASE_DIR???�당 ?�렉?�리(?�는 �??�의 버전 ?�렉?�리)�??�정

    ?�시:
      ZIP: sparrow-enterprise-server-windows-2603.2.zip
      결과: C:\\Sparrow\\sparrow-enterprise-server-windows-2603.2\\(?�축 ?�용)

    Args:
        config: ?�이?�트 ?�정 (package_path, install_dir ?�요)

    Returns:
        True: ?�공
        False: ?�패
    """
    zip_path = config.package_path

    if not zip_path.exists():
        console.print(f"  [FAIL] ZIP ?�일??찾을 ???�습?�다: {zip_path}", style="red")
        return False

    if not zipfile.is_zipfile(zip_path):
        console.print(f"  [FAIL] ?�효??ZIP ?�일???�닙?�다: {zip_path}", style="red")
        return False

    # ZIP ?�일�??�장???�거)?�로 ?�???�렉?�리 ?�성
    zip_stem = zip_path.stem   # e.g. sparrow-enterprise-server-windows-2603.2
    target_dir = config.install_dir / zip_stem
    ensure_dir(target_dir)

    console.print(f"  >> ?�축 ?�제 ?�???�렉?�리: {target_dir}", style="cyan")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            total = len(members)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[PKG] ?�키지 ?�축 ?�제 �?..",
                    total=total,
                )

                for member in members:
                    zf.extract(member, target_dir)
                    progress.update(task, advance=1)

        console.print(
            f"  [ OK ] ?�축 ?�제 ?�료: {target_dir}",
            style="green",
        )

        # BASE_DIR 결정: target_dir ??버전 ?�렉?�리가 ?�으�?그것???�용, ?�으�?target_dir
        base_dir = _detect_version_dir(target_dir) or target_dir
        config.base_dir = base_dir
        os.environ["BASE_DIR"] = str(base_dir)

        if base_dir != target_dir:
            console.print(
                f"  [ OK ] BASE_DIR ?�정 (버전 ?�더 감�?): {base_dir}",
                style="green",
            )
        else:
            console.print(
                f"  [ OK ] BASE_DIR ?�정: {base_dir}",
                style="green",
            )

        return True

    except zipfile.BadZipFile as e:
        console.print(f"  [FAIL] ZIP ?�일 ?�상: {e}", style="red")
        return False
    except PermissionError as e:
        console.print(f"  [FAIL] 권한 ?�류: {e}", style="red")
        return False
    except OSError as e:
        console.print(f"  [FAIL] ?�일 ?�스???�류: {e}", style="red")
        return False


def _detect_version_dir(search_root: Path) -> Path | None:
    """
    지?�된 루트 ?�래?�서 Sparrow 버전 ?�렉?�리�??�동 ?��??�니??

    ?�턴: sparrow-enterprise-server-(windows|linux)-[0-9.]+

    Args:
        search_root: ?�색 ?�작 경로

    Returns:
        발견??버전 ?�렉?�리 Path ?�는 None
    """
    pattern = re.compile(VERSION_PATTERN)

    # 1�? 직접 ?�위 ?�렉?�리
    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir() and pattern.match(child.name):
                return child

    # 2�? ???�계 ???�색
    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir():
                for grandchild in child.iterdir():
                    if grandchild.is_dir() and pattern.match(grandchild.name):
                        return grandchild

    return None
