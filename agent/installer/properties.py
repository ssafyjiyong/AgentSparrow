# -*- coding: utf-8 -*-
"""
sparrow.properties 자동 구성
- 네트워크 설정 (IP 주입)
- 언어 및 관리자 설정
- 모듈 비활성화
- 멱등성 보장
"""
from pathlib import Path
from typing import Optional

from agent.config import AgentConfig, Language, DISABLED_MODULES, OPTIONAL_MODULES


class PropertiesManager:
    """sparrow.properties 파일 관리자 (멱등성 보장)"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lines: list[str] = []
        self._properties: dict[str, str] = {}
        self._load()

    def _load(self):
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.lines = f.readlines()

            for line in self.lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, value = stripped.partition("=")
                    self._properties[key.strip()] = value.strip()

    def get(self, key: str) -> Optional[str]:
        return self._properties.get(key)

    def has(self, key: str) -> bool:
        return key in self._properties

    def set(self, key: str, value: str) -> bool:
        if self.has(key) and self.get(key) == value:
            return False

        if self.has(key):
            for i, line in enumerate(self.lines):
                stripped = line.strip()
                if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                    self.lines[i] = f"{key}={value}\n"
                    break
        else:
            self.lines.append(f"{key}={value}\n")

        self._properties[key] = value
        return True

    def prepend(self, key: str, value: str) -> bool:
        if self.has(key):
            if self.get(key) == value:
                return False
            return self.set(key, value)

        self.lines.insert(0, f"{key}={value}\n")
        self._properties[key] = value
        return True

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.writelines(self.lines)


def patch_properties(config: AgentConfig) -> bool:
    """
    sparrow.properties 파일을 자동 패치합니다.

    Returns:
        True: 성공
        False: 실패
    """
    if not config.base_dir:
        print("  [FAIL] BASE_DIR이 설정되지 않았습니다.")
        return False

    props_path = config.base_dir / "sparrow.properties"
    if not props_path.exists():
        print(f"  [FAIL] sparrow.properties 파일을 찾을 수 없습니다: {props_path}")
        return False

    try:
        pm = PropertiesManager(props_path)
        changes_made = 0

        # 단계 1. 네트워크 설정 적용
        if config.local_ip:
            if pm.set("service.host", config.local_ip):
                changes_made += 1
                print(f"  [NET] service.host = {config.local_ip}")
            if pm.set("service.public.host", config.local_ip):
                changes_made += 1
                print(f"  [NET] service.public.host = {config.local_ip}")
        else:
            print("  [WARN] 로컬 IP가 설정되지 않아 네트워크 설정을 건너뜁니다.")

        # 단계 2. 언어 및 관리자 설정 적용
        if config.language in (Language.EN, Language.JA):
            locale_value = config.language.value
            if pm.prepend("install.locale", locale_value):
                changes_made += 1
                print(f"  [LANG] install.locale = {locale_value}")
            if pm.prepend("install.administrator.id", "admin"):
                changes_made += 1
                print("  [USER] install.administrator.id = admin")
        else:
            print("  [LANG] 한국어(ko) 선택: 기본 언어 설정 유지")

        # 단계 3. 모듈 강제 비활성화 적용
        for module_key, module_value in DISABLED_MODULES.items():
            if pm.set(module_key, module_value):
                changes_made += 1
                print(f"  [CFG] {module_key} = {module_value}")

        # 단계 4. 선택적 모듈 (sast / dast / sca) 적용
        print("  [CFG] 선택 모듈 설정:")
        for module in OPTIONAL_MODULES:
            key = f"service.{module}.enabled"
            value = "true" if module in config.enabled_optional_modules else "false"
            if pm.set(key, value):
                changes_made += 1
            status = "ON " if value == "true" else "OFF"
            print(f"  [CFG]   {key} = {value} ({status})")

        pm.save()

        if changes_made > 0:
            print(f"  [ OK ] sparrow.properties 패치 완료 ({changes_made}개 항목 변경)")
        else:
            print("  [ OK ] sparrow.properties 이미 최신 상태 (변경 없음)")

        return True

    except Exception as e:
        print(f"  [FAIL] Properties 패치 실패: {e}")
        return False
