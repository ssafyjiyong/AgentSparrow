# -*- coding: utf-8 -*-
"""
DB 프로파일 및 리포트 파일 다국어 패치
- .profile / .template 파일 내 한국어 → 외국어 변환
- LLM 사용 적응 번역
- 불필요한 한국어 파일 자동 삭제
"""
import json
import re
from pathlib import Path

from agent.config import AgentConfig, Language
from agent.llm.base import LLMClient

# 한글 유니코드 범위 정규식
KOREAN_PATTERN = re.compile(r"[\uAC00-\uD7AF]+")

# 한국어 전용으로 간주하는 파일명 패턴 (en/ja 선택 시 삭제)
KO_ONLY_FILE_PATTERNS = [
    re.compile(r".*korean.*", re.IGNORECASE),
    re.compile(r".*한국.*", re.IGNORECASE),
    re.compile(r".*_ko\..*"),
    re.compile(r".*-ko\..*"),
]


def _contains_korean(text: str) -> bool:
    return bool(KOREAN_PATTERN.search(text))


def _is_ko_only_file(filename: str) -> bool:
    return any(p.match(filename) for p in KO_ONLY_FILE_PATTERNS)


def _translate_content(
    content: str,
    target_lang: str,
    llm_client: LLMClient,
    file_path: Path,
) -> str:
    try:
        data = json.loads(content)
        translated_data = _translate_json_values(data, target_lang, llm_client)
        return json.dumps(translated_data, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, ValueError):
        pass

    if _contains_korean(content):
        try:
            return llm_client.translate(content, "ko", target_lang)
        except Exception as e:
            print(f"    [WARN] 번역 실패 ({file_path.name}): {e}")
            return content

    return content


def _translate_json_values(data, target_lang: str, llm_client: LLMClient):
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
    DB 프로파일 및 리포트 파일을 다국어 패치합니다.

    Returns:
        True: 성공
        False: 실패
    """
    if config.language == Language.KO:
        print("  [LANG] 한국어(ko) 선택: DB 프로파일 번역을 건너뜁니다.")
        return True

    if not config.base_dir:
        print("  [FAIL] BASE_DIR이 설정되지 않았습니다.")
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
            print(f"  [WARN] 디렉터리가 존재하지 않습니다: {target_dir}")
            continue

        target_files = []
        for ext in ("*.profile", "*.template"):
            target_files.extend(target_dir.rglob(ext))

        if not target_files:
            print(f"  [INFO] 처리할 파일이 없습니다: {target_dir}")
            continue

        total = len(target_files)
        print(f"  >> {target_dir.name} 번역 중... ({total}개 파일)")

        for i, file_path in enumerate(target_files, 1):
            if _is_ko_only_file(file_path.name):
                try:
                    file_path.unlink()
                    total_deleted += 1
                    print(f"    [DEL] 삭제: {file_path.name}")
                except OSError:
                    pass
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="euc-kr")
                except Exception:
                    total_skipped += 1
                    continue

            if _contains_korean(content):
                translated = _translate_content(
                    content, target_lang, llm_client, file_path
                )
                file_path.write_text(translated, encoding="utf-8")
                total_translated += 1
            else:
                total_skipped += 1

            if i % 10 == 0 or i == total:
                print(f"  >> {i}/{total} 처리 완료...")

    print(
        f"  [ OK ] DB 프로파일 패치 완료 "
        f"(번역: {total_translated}, 삭제: {total_deleted}, 스킵: {total_skipped})"
    )
    return True
