import sys
sys.path.insert(0, '.')

from agent.config import LLMProvider
from agent.llm.base import create_llm_client

import os
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD9UUFI6PH_mARsZ3qxXmNrGf6T-ijaZo0")

print('Testing GeminiClient.validate_key() ...')
client = create_llm_client(LLMProvider.GEMINI, API_KEY)
result = client.validate_key()
print(f'validate_key() = {result}')

if result:
    print('[ OK ] API Key 검증 성공!')
else:
    print('[FAIL] API Key 검증 실패')
