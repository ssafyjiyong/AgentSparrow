"""
Gemini API 직접 연결 테스트
- SDK 패턴이 올바르게 작동하는지 확인
- 에러 메시지까지 출력
"""
import sys
sys.path.insert(0, '.')

from google import genai

# 환경변수에서 키 먼저 시도, 없으면 test_gemini.py 하드코딩 키 사용
import os
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD9UUFI6PH_mARsZ3qxXmNrGf6T-ijaZo0")

print(f"사용 키: {API_KEY[:10]}...")
print("SDK 패턴 테스트: client.models.generate_content()")

try:
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Say OK"
    )
    print(f"[ OK ] 응답: {response.text.strip()}")
except Exception as e:
    print(f"[오류] {type(e).__name__}: {e}")
