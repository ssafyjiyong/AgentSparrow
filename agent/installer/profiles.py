# -*- coding: utf-8 -*-
"""
DB ?�로?�일 �?리포???�일 ?�국???�치
- .profile / .template ?�일 ???��? ???�문/?�문 변??
- LLM ?�용 ?�적 번역
- 불필?�한 ?�국???�일 ?�동 ??��
"""
import json
import re
from pathlib import Path

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from agent.config import AgentConfig, Language
from agent.llm.base import LLMClient

console = Console(force_terminal=True, legacy_windows=False)

# ?��? ?�니코드 범위 ?�규??
KOREAN_PATTERN = re.compile(r"[\uAC00-\uD7AF]+")

# ?�국???�용?�로 간주?�는 ?�일�??�턴 (en/ja ?�택 ????��)
KO_ONLY_FILE_PATTERNS = [
    re.compile(r".*korean.*", re.IGNORECASE),
    re.compile(r".*?�국.*", re.IGNORECASE),
    re.compile(r".*_ko\..*"),
    re.compile(r".*-ko\..*"),
]


def _contains_korean(text: str) -> bool:
    """?�스?�에 ?��????�함?�어 ?�는지 ?�인?�니??"""
    return bool(KOREAN_PATTERN.search(text))


def _is_ko_only_file(filename: str) -> bool:
    """?�국???�용 ?�일?��? ?�인?�니??"""
    return any(p.match(filename) for p in KO_ONLY_FILE_PATTERNS)


def _translate_content(
    content: str,
    target_lang: str,
    llm_client: LLMClient,
    file_path: Path,
) -> str:
    """
    ?�일 ?�용??번역?�니??
    JSON ?�식?�면 구조�?보존?�고 값만 번역?�니??

    Args:
        content: ?�본 ?�용
        target_lang: 목표 ?�어 (en/ja)
        llm_client: LLM ?�라?�언??
        file_path: ?�일 경로 (?�버그용)

    Returns:
        번역???�용
    """
    # JSON ?�일?��? ?�인
    try:
        data = json.loads(content)
        # JSON 구조 ??value�?번역
        translated_data = _translate_json_values(data, target_lang, llm_client)
        return json.dumps(translated_data, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, ValueError):
        pass

    # ?�반 ?�스?????�체 번역
    if _contains_korean(content):
        try:
            return llm_client.translate(content, "ko", target_lang)
        except Exception as e:
            console.print(
                f"    [WARN] 번역 ?�패 ({file_path.name}): {e}",
                style="yellow",
            )
            return content

    return content


def _translate_json_values(data, target_lang: str, llm_client: LLMClient):
    """JSON 값만 ?��??�으�?번역?�니??(?�는 보존)."""
    if isinstance(data, dict):
        return {
            key: _translate_json_values(value, target_lang, llm_client)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            _translate_json_values(item, target_lang, llm_client)
            for item in data
        ]
    elif isinstance(data, str) and _contains_korean(data):
        try:
            return llm_client.translate(data, "ko", target_lang)
        except Exception:
            return data
    else:
        return data


def patch_profiles(config: AgentConfig, llm_client: LLMClient) -> bool:
    """
    DB ?�로?�일 �?리포???�일???�국???�치?�니??

    Args:
        config: ?�이?�트 ?�정
        llm_client: LLM ?�라?�언??

    Returns:
        True: ?�공
        False: ?�패
    """
    if config.language == Language.KO:
        console.print(
            "  [LANG] ?�국??ko) ?�택: DB ?�로?�일 번역??건너?�니??",
            style="dim",
        )
        return True

    if not config.base_dir:
        console.print("  [FAIL] BASE_DIR???�정?��? ?�았?�니??", style="red")
        return False

    target_lang = config.language.value
    target_dirs = [
        config.base_dir / "db" / "profiles",
        config.base_dir / "db" / "reports",
    ]

    total_translated = 0
    total_deleted = 0
    total_skipped = 0

    for target_dir in target_dirs:
        if not target_dir.exists():
            console.print(
                f"  [WARN] ?�렉?�리가 존재?��? ?�습?�다: {target_dir}",
                style="yellow",
            )
            continue

        # ?�???�일 ?�집
        target_files = []
        for ext in ("*.profile", "*.template"):
            target_files.extend(target_dir.rglob(ext))

        if not target_files:
            console.print(
                f"  [INFO]  처리???�일???�습?�다: {target_dir}",
                style="dim",
            )
            continue

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[LANG] {target_dir.name} 번역 �?..",
                total=len(target_files),
            )

            for file_path in target_files:
                # ?�국???�용 ?�일 ??��
                if _is_ko_only_file(file_path.name):
                    try:
                        file_path.unlink()
                        total_deleted += 1
                        console.print(
                            f"    [DEL]  ??��: {file_path.name}",
                            style="dim red",
                        )
                    except OSError:
                        pass
                    progress.update(task, advance=1)
                    continue

                # ?�일 ?�기 �?번역
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        content = file_path.read_text(encoding="euc-kr")
                    except Exception:
                        total_skipped += 1
                        progress.update(task, advance=1)
                        continue

                if _contains_korean(content):
                    translated = _translate_content(
                        content, target_lang, llm_client, file_path
                    )
                    file_path.write_text(translated, encoding="utf-8")
                    total_translated += 1
                else:
                    total_skipped += 1

                progress.update(task, advance=1)

    # 결과 ?�약
    console.print(
        f"  [ OK ] DB ?�로?�일 ?�치 ?�료 "
        f"(번역: {total_translated}, ??��: {total_deleted}, ?�킵: {total_skipped})",
        style="green",
    )
    return True
