# Sparrow Enterprise Server Installation Agent (CLI)

터미널 기반 CLI 에이전트로, Sparrow Enterprise Server의 사전 검증, 파일 구성(properties/profiles), 설치 및 실행 과정을 자동화합니다.

## 주요 기능

- **대화형 CLI**: Rich UI를 통한 직관적인 설정 입력 (LLM 선택, API Key, 언어, 패키지 경로)
- **사전 환경 점검**: 실행 권한, 포트 충돌, 필수 패키지 자동 검사
- **자동 설치 파이프라인**: ZIP 해제 → Properties 패치 → 다국어 변환 → 서비스 실행
- **LLM 통합**: Gemini / GPT / Claude를 활용한 다국어 번역 및 로그 분석
- **멱등성 보장**: 중복 실행에도 설정이 누적되지 않음

## 시스템 요구사항

- **Python**: 3.10+
- **OS**: Windows 10+ / Linux (Ubuntu 20.04+)
- **LLM API Key**: Gemini, OpenAI GPT, 또는 Anthropic Claude 중 하나

## 설치 및 실행

### 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 에이전트 실행
python main.py
```

### 빌드 (단일 실행 파일)

```bash
# PyInstaller 설치
pip install pyinstaller

# 빌드
python build.py

# 실행 파일 위치: dist/sparrow-agent.exe (Windows) 또는 dist/sparrow-agent (Linux)
```

## 사용 방법

1. 터미널에서 `python main.py` (또는 빌드된 `.exe`) 실행
2. LLM 제공자 선택 (Gemini / GPT / Claude)
3. API Key 입력 (마스킹 처리)
4. 설치 언어 선택 (ko / en / ja)
5. Sparrow Enterprise Server `.zip` 파일 경로 입력
6. 자동 설치 파이프라인 실행 (사용자 개입 없음)

## 프로젝트 구조

```
AgentSparrow/
├── main.py                  # 진입점
├── build.py                 # PyInstaller 빌드 스크립트
├── requirements.txt         # Python 의존성
├── pyproject.toml           # 프로젝트 메타데이터
└── agent/                   # 핵심 패키지
    ├── cli.py               # 대화형 CLI 입력 처리
    ├── config.py            # 설정값 데이터 클래스
    ├── checks/              # 사전 환경 점검
    │   ├── permissions.py   #   권한 검증
    │   ├── ports.py         #   포트 충돌 검사
    │   └── packages.py      #   필수 패키지 확인
    ├── installer/           # 설치 파이프라인
    │   ├── extractor.py     #   ZIP 해제 및 경로 최적화
    │   ├── properties.py    #   sparrow.properties 자동 구성
    │   ├── profiles.py      #   DB 프로파일 다국어 패치
    │   └── runner.py        #   서비스 실행 및 헬스 체크
    ├── llm/                 # LLM 통합
    │   ├── base.py          #   추상 클라이언트 + 팩토리
    │   ├── gemini.py        #   Google Gemini
    │   ├── openai_client.py #   OpenAI GPT
    │   ├── claude.py        #   Anthropic Claude
    │   └── prompts.py       #   프롬프트 템플릿
    └── utils/               # 유틸리티
        ├── network.py       #   네트워크 (IP 추출)
        └── platform_utils.py #  OS 판별
```

## 라이선스

Internal Use Only
