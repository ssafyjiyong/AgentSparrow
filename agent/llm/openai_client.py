"""
OpenAI GPT LLM 클라이언트
"""
from agent.llm.base import LLMClient
from agent.llm.prompts import (
    TRANSLATE_SYSTEM_PROMPT,
    LOG_ANALYSIS_SYSTEM_PROMPT,
    get_translate_prompt,
    get_log_analysis_prompt,
)


class OpenAIClient(LLMClient):
    """OpenAI GPT API 클라이언트"""

    MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._client = None

    def _get_client(self):
        """OpenAI 클라이언트를 Lazy 초기화합니다."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def validate_key(self) -> bool:
        """OpenAI API 키 유효성 검증"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception:
            return False

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """GPT를 사용한 텍스트 번역"""
        client = self._get_client()
        prompt = get_translate_prompt(text, source_lang, target_lang)
        response = client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    def analyze_log(self, log_content: str, context: str = "") -> str:
        """GPT를 사용한 로그 분석"""
        client = self._get_client()
        prompt = get_log_analysis_prompt(log_content, context)
        response = client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": LOG_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    def get_provider_name(self) -> str:
        return "OpenAI GPT"
