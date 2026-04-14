"""
Google Gemini LLM 클라이언트
- SDK: google-genai (신 버전)
- 공식 예시 패턴:
    from google import genai
    client = genai.Client(api_key=...)
    response = client.models.generate_content(model=..., contents=...)
- validate_key: 짧은 generate_content 호출로 확인 (models.list 전체 로드 방지)
"""
from agent.llm.base import LLMClient
from agent.llm.prompts import (
    TRANSLATE_SYSTEM_PROMPT,
    LOG_ANALYSIS_SYSTEM_PROMPT,
    get_translate_prompt,
    get_log_analysis_prompt,
)


class GeminiClient(LLMClient):
    """Google Gemini API 클라이언트 (google-genai SDK)"""

    MODEL = "gemini-3-flash-preview"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._client = None

    def _get_client(self):
        """google.genai 클라이언트를 Lazy 초기화합니다."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def validate_key(self) -> bool:
        """
        Gemini API 키 유효성 검증.
        짧은 generate_content 호출로 확인합니다.
        (models.list() 전체 페이지 로드 방지)
        """
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.MODEL,
                contents="hi",
            )
            return bool(response.text)
        except Exception:
            return False

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Gemini를 사용한 텍스트 번역"""
        from google.genai import types
        client = self._get_client()
        prompt = get_translate_prompt(text, source_lang, target_lang)
        response = client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TRANSLATE_SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )
        return response.text.strip()

    def analyze_log(self, log_content: str, context: str = "") -> str:
        """Gemini를 사용한 로그 분석"""
        from google.genai import types
        client = self._get_client()
        prompt = get_log_analysis_prompt(log_content, context)
        response = client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=LOG_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.3,
            ),
        )
        return response.text.strip()

    def get_provider_name(self) -> str:
        return "Google Gemini"
