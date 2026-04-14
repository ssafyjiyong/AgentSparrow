"""
LLM 프롬프트 템플릿
- 번역 프롬프트 (JSON 구조 보존)
- 로그 분석 프롬프트
"""


TRANSLATE_SYSTEM_PROMPT = """You are a professional translator specializing in software localization.
Your task is to translate text while strictly preserving the original structure and format.

CRITICAL RULES:
1. If the input is JSON, preserve ALL keys exactly as-is. Only translate the values.
2. Do NOT translate technical terms, variable names, or placeholders (e.g., {{variable}}, %s, {0}).
3. Maintain the exact same line breaks, indentation, and special characters.
4. Return ONLY the translated content with no additional explanation or wrapping.
"""


def get_translate_prompt(text: str, source_lang: str, target_lang: str) -> str:
    """번역 프롬프트를 생성합니다."""
    lang_names = {
        "ko": "Korean",
        "en": "English",
        "ja": "Japanese",
    }
    src = lang_names.get(source_lang, source_lang)
    tgt = lang_names.get(target_lang, target_lang)
    return (
        f"Translate the following text from {src} to {tgt}.\n"
        f"Preserve the exact structure and format.\n\n"
        f"--- BEGIN TEXT ---\n{text}\n--- END TEXT ---"
    )


LOG_ANALYSIS_SYSTEM_PROMPT = """You are an expert system administrator and DevOps engineer.
Your task is to analyze server installation/startup log files and provide actionable diagnosis.

RESPONSE FORMAT (in Korean):
1. **오류 원인**: Clearly identify the root cause of the error.
2. **영향 범위**: Describe which components or services are affected.
3. **조치 방법**: Provide step-by-step instructions to resolve the issue.
4. **추가 확인**: Suggest any additional checks or diagnostic commands.

Keep your response concise and actionable.
"""


def get_log_analysis_prompt(log_content: str, context: str = "") -> str:
    """로그 분석 프롬프트를 생성합니다."""
    prompt = "다음 서버 설치/구동 로그에서 발생한 오류를 분석하고 해결 방법을 제시해 주세요.\n\n"
    if context:
        prompt += f"컨텍스트: {context}\n\n"
    prompt += f"--- LOG START ---\n{log_content}\n--- LOG END ---"
    return prompt
