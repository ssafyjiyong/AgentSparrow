"""
LLM 클라이언트 추상 베이스 클래스 및 팩토리 함수
"""
from abc import ABC, abstractmethod
from typing import Optional

from agent.config import LLMProvider


class LLMClient(ABC):
    """LLM 클라이언트 추상 베이스 클래스"""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @abstractmethod
    def validate_key(self) -> bool:
        """
        API 키의 유효성을 검증합니다.
        간단한 테스트 호출을 통해 확인합니다.

        Returns:
            True이면 유효한 키
        """
        ...

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        텍스트를 번역합니다. 구조(JSON 등)를 보존합니다.

        Args:
            text: 번역할 텍스트
            source_lang: 소스 언어 코드 (ko, en, ja)
            target_lang: 타겟 언어 코드 (ko, en, ja)

        Returns:
            번역된 텍스트
        """
        ...

    @abstractmethod
    def analyze_log(self, log_content: str, context: str = "") -> str:
        """
        서버 로그를 분석하여 오류 원인 및 해결 방법을 제시합니다.

        Args:
            log_content: 분석할 로그 내용
            context: 추가 컨텍스트 (예: 설치 단계)

        Returns:
            분석 결과 문자열
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """LLM 제공자 이름을 반환합니다."""
        ...


def create_llm_client(provider: LLMProvider, api_key: str) -> LLMClient:
    """
    LLM 제공자에 따른 클라이언트 인스턴스를 생성합니다.

    Args:
        provider: LLM 제공자 enum
        api_key: API 키

    Returns:
        LLMClient 구현체

    Raises:
        ValueError: 지원하지 않는 제공자인 경우
    """
    if provider == LLMProvider.GEMINI:
        from agent.llm.gemini import GeminiClient
        return GeminiClient(api_key)
    elif provider == LLMProvider.GPT:
        from agent.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key)
    elif provider == LLMProvider.CLAUDE:
        from agent.llm.claude import ClaudeClient
        return ClaudeClient(api_key)
    else:
        raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
