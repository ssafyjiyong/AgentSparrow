"""
Anthropic Claude LLM 클라이언트
"""
from agent.llm.base import LLMClient
from agent.llm.prompts import (
    TRANSLATE_SYSTEM_PROMPT,
    LOG_ANALYSIS_SYSTEM_PROMPT,
    get_translate_prompt,
    get_log_analysis_prompt,
)


class ClaudeClient(LLMClient):
    """Anthropic Claude API 클라이언트"""

    MODEL = "claude-3-5-haiku-latest"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._client = None

    def _get_client(self):
        """Anthropic 클라이언트를 Lazy 초기화합니다."""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def validate_key(self) -> bool:
        """Claude API 키 유효성 검증"""
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'ok'"}],
            )
            return response.content[0].text is not None
        except Exception:
            return False

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Claude를 사용한 텍스트 번역"""
        client = self._get_client()
        prompt = get_translate_prompt(text, source_lang, target_lang)
        response = client.messages.create(
            model=self.MODEL,
            max_tokens=4096,
            system=TRANSLATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def analyze_log(self, log_content: str, context: str = "") -> str:
        """Claude를 사용한 로그 분석"""
        client = self._get_client()
        prompt = get_log_analysis_prompt(log_content, context)
        response = client.messages.create(
            model=self.MODEL,
            max_tokens=4096,
            system=LOG_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def get_provider_name(self) -> str:
        return "Anthropic Claude"
