"""
에이전트 설정 데이터 클래스 및 상수 정의
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import platform
from typing import Optional


class LLMProvider(Enum):
    """지원하는 LLM 제공자"""
    GEMINI = "gemini"
    GPT = "gpt"
    CLAUDE = "claude"


class Language(Enum):
    """지원하는 설치 언어"""
    KO = "ko"
    EN = "en"
    JA = "ja"


class OSType(Enum):
    """지원하는 OS 타입"""
    WINDOWS = "windows"
    LINUX = "linux"


# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

REQUIRED_PORTS = [
    10880, 10881, 10500, 10510, 10610, 10700, 10800, 10900,
    10910, 10920, 10930, 10950, 11010, 11020, 11030, 11040,
    11050, 10520, 10620, 10621, 8888, 61616, 8161,
]

INSTALL_PATHS = {
    OSType.WINDOWS: Path("C:/Sparrow"),
    OSType.LINUX: Path("/opt/sparrow"),
}

VERSION_PATTERN = r"sparrow-enterprise-server-(windows|linux)-[\d.]+"

# sparrow.properties 강제 비활성화 모듈
DISABLED_MODULES = {
    "service.rasp.enabled": "false",
    "service.tso.enabled": "false",
    "service.eureka.enabled": "false",
}

# 선택 가능한 선택적 모듈 (사용자가 on/off 결정)
OPTIONAL_MODULES = ["sast", "dast", "sca"]

# Linux 필수 패키지
LINUX_REQUIRED_PACKAGES = ["unzip", "fontconfig"]
LINUX_REQUIRED_LIBS = ["libtinfo.so.5", "libldap_r-2.4.so.2"]


@dataclass
class AgentConfig:
    """에이전트 실행에 필요한 모든 설정값을 저장합니다."""

    # 사용자 입력
    llm_provider: LLMProvider = LLMProvider.GEMINI
    api_key: str = ""
    language: Language = Language.KO
    package_path: Path = Path()

    # 선택적 모듈 활성화 목록 (sast, dast, sca 중 선택)
    enabled_optional_modules: list = field(default_factory=list)

    # 자동 감지
    os_type: OSType = field(default_factory=lambda: (
        OSType.WINDOWS if platform.system() == "Windows" else OSType.LINUX
    ))

    # 설치 과정에서 결정
    install_dir: Path = Path()
    base_dir: Optional[Path] = None
    local_ip: str = ""

    def __post_init__(self):
        if not self.install_dir or self.install_dir == Path():
            self.install_dir = INSTALL_PATHS.get(self.os_type, Path("C:/Sparrow"))

    @property
    def is_windows(self) -> bool:
        return self.os_type == OSType.WINDOWS

    @property
    def is_linux(self) -> bool:
        return self.os_type == OSType.LINUX
