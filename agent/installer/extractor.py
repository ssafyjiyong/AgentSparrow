# -*- coding: utf-8 -*-
"""
패키지 압축 해제 및 경로 최적화
- ZIP 파일 이름으로 동일한 디렉터리를 install_dir 아래에 생성
- 그 안에 압축 해제
- BASE_DIR 환경 변수 매핑
"""
import os
import re
import zipfile
from pathlib import Path

from agent.config import AgentConfig, VERSION_PATTERN
from agent.utils.platform_utils import ensure_dir


def extract_package(config: AgentConfig) -> bool:
    """
    Sparrow Enterprise Server 패키지를 압축 해제합니다.

    Returns:
        True: 성공
        False: 실패
    """
    zip_path = config.package_path

    if not zip_path.exists():
        print(f"  [FAIL] ZIP 파일을 찾을 수 없습니다: {zip_path}")
        return False

    if not zipfile.is_zipfile(zip_path):
        print(f"  [FAIL] 유효한 ZIP 파일이 아닙니다: {zip_path}")
        return False

    zip_stem = zip_path.stem
    target_dir = config.install_dir / zip_stem
    ensure_dir(target_dir)

    print(f"  >> 압축 해제 대상 디렉터리: {target_dir}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            total = len(members)
            print(f"  >> 파일 수: {total}개 압축 해제 중...")

            for i, member in enumerate(members, 1):
                zf.extract(member, target_dir)
                if i % 500 == 0 or i == total:
                    print(f"  >> {i}/{total} 완료...")

        print(f"  [ OK ] 압축 해제 완료: {target_dir}")

        base_dir = _detect_version_dir(target_dir) or target_dir
        config.base_dir = base_dir
        os.environ["BASE_DIR"] = str(base_dir)

        if base_dir != target_dir:
            print(f"  [ OK ] BASE_DIR 설정 (버전 폴더 감지): {base_dir}")
        else:
            print(f"  [ OK ] BASE_DIR 설정: {base_dir}")

        return True

    except zipfile.BadZipFile as e:
        print(f"  [FAIL] ZIP 파일 손상: {e}")
        return False
    except PermissionError as e:
        print(f"  [FAIL] 권한 오류: {e}")
        return False
    except OSError as e:
        print(f"  [FAIL] 파일 시스템 오류: {e}")
        return False


def _detect_version_dir(search_root: Path) -> Path | None:
    """
    지정된 루트 아래에서 Sparrow 버전 디렉터리를 자동 탐지합니다.
    패턴: sparrow-enterprise-server-(windows|linux)-[0-9.]+
    """
    pattern = re.compile(VERSION_PATTERN)

    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir() and pattern.match(child.name):
                return child

    if search_root.is_dir():
        for child in search_root.iterdir():
            if child.is_dir():
                for grandchild in child.iterdir():
                    if grandchild.is_dir() and pattern.match(grandchild.name):
                        return grandchild

    return None
