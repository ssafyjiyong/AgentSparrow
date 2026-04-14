# -*- coding: utf-8 -*-
"""
sparrow.properties ?�동 구성
- ?�트?�크 ?�정 (IP 주입)
- ?�어 �?관리자 ?�정
- 모듈 비활?�화
- 멱등??보장
"""
from pathlib import Path
from typing import Optional

from rich.console import Console

from agent.config import AgentConfig, Language, DISABLED_MODULES, OPTIONAL_MODULES

console = Console(force_terminal=True, legacy_windows=False)


class PropertiesManager:
    """sparrow.properties ?�일 관리자 (멱등??보장)"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lines: list[str] = []
        self._properties: dict[str, str] = {}
        self._load()

    def _load(self):
        """?�일???�어 lines?� properties ?�셔?�리�??�싱?�니??"""
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.lines = f.readlines()

            for line in self.lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, value = stripped.partition("=")
                    self._properties[key.strip()] = value.strip()

    def get(self, key: str) -> Optional[str]:
        """?�성값을 가?�옵?�다."""
        return self._properties.get(key)

    def has(self, key: str) -> bool:
        """?�성??존재?�는지 ?�인?�니??"""
        return key in self._properties

    def set(self, key: str, value: str) -> bool:
        """
        ?�성???�정?�니?? ?��? 존재?�면 값을 ?�데?�트?�고,
        ?�으�??�일 ?�에 추�??�니??

        Returns:
            True: 변경됨, False: ?��? ?�일??�?
        """
        if self.has(key) and self.get(key) == value:
            return False  # 멱등?? ?��? ?�일??�?

        if self.has(key):
            # 기존 ?�인 ?�데?�트
            for i, line in enumerate(self.lines):
                stripped = line.strip()
                if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                    self.lines[i] = f"{key}={value}\n"
                    break
        else:
            # ???�인 추�?
            self.lines.append(f"{key}={value}\n")

        self._properties[key] = value
        return True

    def prepend(self, key: str, value: str) -> bool:
        """
        ?�성???�일 최상?�에 ?�입?�니??(?��? 존재?�면 ?�킵).

        Returns:
            True: 추�??? False: ?��? 존재 (멱등??
        """
        if self.has(key):
            if self.get(key) == value:
                return False  # 멱등?? ?��? ?�일??�?
            # 값이 ?�르�??�데?�트
            return self.set(key, value)

        self.lines.insert(0, f"{key}={value}\n")
        self._properties[key] = value
        return True

    def save(self):
        """변경사??�� ?�일???�?�합?�다."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.writelines(self.lines)


def patch_properties(config: AgentConfig) -> bool:
    """
    sparrow.properties ?�일???�동 ?�치?�니??

    1. ?�트?�크: 로컬 IP ??service.host, service.public.host
    2. ?�어: en/ja ?�택 ??install.administrator.id, install.locale ?�입
    3. 모듈: 강제 비활?�화 ?�정

    Args:
        config: ?�이?�트 ?�정 (base_dir, local_ip, language ?�요)

    Returns:
        True: ?�공
        False: ?�패
    """
    if not config.base_dir:
        console.print("  [FAIL] BASE_DIR???�정?��? ?�았?�니??", style="red")
        return False

    props_path = config.base_dir / "sparrow.properties"
    if not props_path.exists():
        console.print(
            f"  [FAIL] sparrow.properties ?�일??찾을 ???�습?�다: {props_path}",
            style="red",
        )
        return False

    try:
        pm = PropertiesManager(props_path)
        changes_made = 0

        # ?�?� 1. ?�트?�크 ?�정 ?�?�
        if config.local_ip:
            if pm.set("service.host", config.local_ip):
                changes_made += 1
                console.print(
                    f"  [NET] service.host = {config.local_ip}",
                    style="cyan",
                )
            if pm.set("service.public.host", config.local_ip):
                changes_made += 1
                console.print(
                    f"  [NET] service.public.host = {config.local_ip}",
                    style="cyan",
                )
        else:
            console.print(
                "  [WARN] 로컬 IP가 ?�정?��? ?�아 ?�트?�크 ?�정??건너?�니??",
                style="yellow",
            )

        # ?�?� 2. ?�어 �?관리자 ?�정 ?�?�
        if config.language in (Language.EN, Language.JA):
            locale_value = config.language.value
            if pm.prepend("install.locale", locale_value):
                changes_made += 1
                console.print(
                    f"  [LANG] install.locale = {locale_value}",
                    style="cyan",
                )
            if pm.prepend("install.administrator.id", "admin"):
                changes_made += 1
                console.print(
                    "  [USER] install.administrator.id = admin",
                    style="cyan",
                )
        else:
            console.print(
                "  [LANG] ?�국??ko) ?�택: 기본 ?�어 ?�정 ?��?",
                style="dim",
            )

        # ?�?� 3. 모듈 강제 비활?�화 ?�?�
        for module_key, module_value in DISABLED_MODULES.items():
            if pm.set(module_key, module_value):
                changes_made += 1
                console.print(
                    f"  [CFG] {module_key} = {module_value}",
                    style="cyan",
                )

        # ?�?� 4. ?�택??모듈 (sast / dast / sca) ?�?�
        console.print(
            "  [CFG] ?�택 모듈 ?�정:",
            style="bold",
        )
        for module in OPTIONAL_MODULES:
            key = f"service.{module}.enabled"
            value = "true" if module in config.enabled_optional_modules else "false"
            if pm.set(key, value):
                changes_made += 1
            status = "[green]true [/green] (ON) " if value == "true" else "[dim]false (OFF)[/dim]"
            console.print(f"  [CFG]   {key} = {status}", style="cyan")

        pm.save()

        if changes_made > 0:
            console.print(
                f"  [ OK ] sparrow.properties ?�치 ?�료 ({changes_made}�???�� 변�?",
                style="green",
            )
        else:
            console.print(
                "  [ OK ] sparrow.properties ?��? 최신 ?�태 (변�??�음)",
                style="green",
            )

        return True

    except Exception as e:
        console.print(f"  [FAIL] Properties ?�치 ?�패: {e}", style="red")
        return False
