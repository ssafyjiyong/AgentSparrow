"""
?¨í‚¤ì§€ ?•ì¶• ?´ì œ ë°?ê²½ë¡œ ìµœì ??- ZIP ?Œì¼ ?´ë¦„ê³??™ì¼???”ë ‰?°ë¦¬ë¥?install_dir ?„ë˜???ì„±
- ê·??ˆì— ?•ì¶• ?´ì œ
- BASE_DIR ?˜ê²½ ë³€??ë§¤í•‘
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
    Sparrow Enterprise Server ?¨í‚¤ì§€ë¥??•ì¶• ?´ì œ?©ë‹ˆ??

    ê·œì¹™:
    - ZIP ?Œì¼ëª??•ì¥???œì™¸)ê³??™ì¼???´ë¦„???”ë ‰?°ë¦¬ë¥?install_dir ?„ë˜???ì„±
    - ê·??”ë ‰?°ë¦¬ ?ˆì— ?•ì¶• ?´ì œ
    - BASE_DIR???´ë‹¹ ?”ë ‰?°ë¦¬(?ëŠ” ê·??ˆì˜ ë²„ì „ ?”ë ‰?°ë¦¬)ë¡??¤ì •

    ?ˆì‹œ:
      ZIP: sparrow-enterprise-server-windows-2603.2.zip
      ê²°ê³¼: C:\\Sparrow\\sparrow-enterprise-server-windows-2603.2\\(?•ì¶• ?´ìš©)

    Args:
        config: ?ì´?„íŠ¸ ?¤ì • (package_path, install_dir ?„ìš”)

    Returns:
        True: ?±ê³µ
        False: ?¤íŒ¨
    """
    zip_path = config.package_path

    if not zip_path.exists():
        console.print(f"  [FAIL] ZIP ?Œì¼??ì°¾ì„ ???†ìŠµ?ˆë‹¤: {zip_path}", style="red")
        return False

    if not zipfile.is_zipfile(zip_path):
        console.print(f"  [FAIL] ? íš¨??ZIP ?Œì¼???„ë‹™?ˆë‹¤: {zip_path}", style="red")
        return False

    # ZIP ?Œì¼ëª??•ì¥???œê±°)?¼ë¡œ ?€???”ë ‰?°ë¦¬ ?ì„±
    zip_stem = zip_path.stem   # e.g. sparrow-enterprise-server-windows-2603.2
    target_dir = config.install_dir / zip_stem
    ensure_dir(target_dir)

    console.print(f"  >> ?•ì¶• ?´ì œ ?€???”ë ‰?°ë¦¬: {target_dir}", style="cyan")

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
                    "[PKG] ?¨í‚¤ì§€ ?•ì¶• ?´ì œ ì¤?..",
                    total=total,
                )

                for member in members:
                    zf.extract(member, target_dir)
                    progress.update(task, advance=1)

        console.print(
            f"  [ OK ] ?•ì¶• ?´ì œ ?„ë£Œ: {target_dir}",
            style="green",
        )

        # BASE_DIR ê²°ì •: target_dir ??ë²„ì „ ?”ë ‰?°ë¦¬ê°€ ?ˆìœ¼ë©?ê·¸ê²ƒ???¬ìš©, ?†ìœ¼ë©?target_dir
        base_dir = _detect_version_dir(target_dir) or target_dir
        config.base_dir = base_dir
        os.environ["BASE_DIR"] = str(base_dir)

        if base_dir != target_dir:
            console.print(
                f"  [ OK ] BASE_DIR ?¤ì • (ë²„ì „ ?´ë” ê°ì?): {base_dir}",
                style="green",
            )
        else:
            console.print(
                f"  [ OK ] BASE_DIR ?¤ì •: {base_dir}",
                style="green",
            )

        return True

    except zipfile.BadZipFile as e:
        console.print(f"  [FAIL] ZIP ?Œì¼ ?ìƒ: {e}", style="red")
        return False
    except PermissionError as e:
        console.print(f"  [FAIL] ê¶Œí•œ ?¤ë¥˜: {e}", style="red")
        return False
    except OSError as e:
        console.print(f"  [FAIL] ?Œì¼ ?œìŠ¤???¤ë¥˜: {e}", style="red")
        return False


def _detect_version_dir(search_root: Path) -> Path | None:
    """
    ì§€?•ëœ ë£¨íŠ¸ ?„ë˜?ì„œ Sparrow ë²„ì „ ?”ë ‰?°ë¦¬ë¥??ë™ ?ì??©ë‹ˆ??

    ?¨í„´: sparrow-enterprise-server-(windows|linux)-[0-9.]+

    Args:
        search_root: ?ìƒ‰ ?œì‘ ê²½ë¡œ

    Returns:
        ë°œê²¬??ë²„ì „ ?”ë ‰?°ë¦¬ Path ?ëŠ” None
    """
    pattern = re.compile(VERSION_PATTERN)

    # 1ì°? ì§ì ‘ ?˜ìœ„ ?”ë ‰?°ë¦¬
    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir() and pattern.match(child.name):
                return child

    # 2ì°? ???¨ê³„ ???ìƒ‰
    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir():
                for grandchild in child.iterdir():
                    if grandchild.is_dir() and pattern.match(grandchild.name):
                        return grandchild

    return None
