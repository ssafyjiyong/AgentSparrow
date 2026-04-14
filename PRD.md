# Product Requirements Document (PRD)
**Project Name:** Sparrow Enterprise Server Installation Agent (CLI)
**Version:** 1.0.0
**Target Platform:** Windows (.exe), Linux (Binary)
**Framework:** Antigravity (Terminal UI)

---

## 1. 프로젝트 개요 (Overview)
본 프로젝트는 기존 수동으로 진행되던 Sparrow Enterprise Server의 복잡한 사전 검증, 파일 구성(properties/profiles), 설치 및 실행 과정을 단일 실행 파일(.exe/binary)로 자동화하는 터미널 기반 에이전트를 개발하는 것을 목표로 합니다. 특히, 사용자가 입력한 LLM API를 활용하여 설치 로그 분석 및 다국어 텍스트 치환 작업을 보조하여 설치 성공률과 편의성을 극대화합니다.

## 2. 사용자 플로우 (User Flow)
사용자가 터미널에서 에이전트 실행 시 다음 순서로 인터랙션이 진행됩니다.

1. **에이전트 실행:** 터미널에서 `.exe` (또는 Linux 바이너리) 실행
2. **LLM 및 API Key 설정:** - LLM 제공자 선택 (Gemini / GPT / Claude)
   - 해당 LLM의 API Key 입력 (입력값 마스킹 처리)
3. **언어 선택:** 설치될 Sparrow 환경의 언어 선택 (ko / en / ja)
4. **패키지 위치 지정:** Sparrow Enterprise Server의 `.zip` 파일 로컬 경로 입력
5. **자동 설치 파이프라인 시작:** (사용자 개입 없음)
   - 사전 점검 (권한, 포트, 필수 패키지) -> 압축 해제 -> 속성 파일 자동 패치 -> DB 프로파일 및 템플릿 언어 변환 -> 서비스 설치 및 구동 -> 헬스 체크
6. **결과 출력:** 성공 메시지 또는 실패 시 LLM 기반 로그 분석 리포트 출력

## 3. 핵심 기능 요구사항 (Functional Requirements)

### 3.1. 대화형 CLI 입력 처리
* **기술 사양:** 터미널 내에서 방향키 및 텍스트 입력을 통해 설정값을 수집합니다.
* **입력 검증:** 압축 파일 경로가 유효한지(.zip 확장자 및 파일 존재 여부) 즉시 검증합니다.

### 3.2. 사전 환경 점검 (Pre-requisites Check)
제공된 기준에 따라 설치 전 필수 환경을 스캔하고, 조건 미달 시 즉시 중단(Exit)합니다.
* **실행 권한 검증:**
  * Windows: 관리자(Admin) 권한으로 실행되었는지 확인 후, **일반 사용자(User) 권한으로 재실행하도록 안내** (PostgreSQL 구동 제약).
  * Linux: `root` 계정으로 실행되었는지 확인 후, 일반 사용자 권한 요구.
* **포트 충돌 검사:**
  * 점검 대상 포트: `10880, 10881, 10500, 10510, 10610, 10700, 10800, 10900, 10910, 10920, 10930, 10950, 11010, 11020, 11030, 11040, 11050, 10520, 10620, 10621, 8888, 61616, 8161`
* **필수 패키지 확인 (OS별):**
  * Windows: `vc_redist.x64.exe` 설치 여부 확인 및 필요시 패키지 내 파일 자동 실행.
  * Linux: `unzip`, `fontconfig`, `libtinfo.so.5`, `libldap_r-2.4.so.2` (OS 패키지 매니저를 통해 사전 점검).

### 3.3. 패키지 압축 해제 및 경로 최적화
* **설치 경로:** 권장 경로인 `C:\Sparrow\` (Windows) 또는 `/opt/sparrow/` (Linux) 아래에 압축을 해제합니다.
* **동적 디렉토리 인식:** 릴리즈마다 변경되는 버전명(예: `sparrow-enterprise-server-windows-2603.2`)을 정규식(`sparrow-enterprise-server-(windows|linux)-[0-9.]+`)으로 스캔하여 BASE_DIR 환경 변수로 자동 매핑합니다.

### 3.4. sparrow.properties 자동 구성
압축 해제된 폴더 내의 `sparrow.properties` 파일을 읽어 다음 작업을 수행합니다.
* **네트워크:** 로컬 IPv4 주소를 자동 추출하여 `service.host` 및 `service.public.host`에 주입 (localhost 할당 방지).
* **언어 및 관리자:** 선택한 언어(en, ja)에 따라 `install.administrator.id=admin` 및 `install.locale=en|ja` 항목을 최상단에 삽입. (ko 선택 시 기본값 유지).
* **모듈 설정 강제:** * `service.rasp.enabled=false`
  * `service.tso.enabled=false`
  * `service.eureka.enabled=false`
  * (log, plugin, sast, dast, sca는 기본 설정값 유지)

### 3.5. DB 프로파일 및 리포트 파일 다국어 패치
* **대상 경로:** `[BASE_DIR]/db/profiles`, `[BASE_DIR]/db/reports`
* **처리 로직:** 사용자가 'en' 또는 'ja'를 선택한 경우, 해당 폴더 내의 `.profile` 및 `.template` 파일들에 포함된 한글 문자열을 영문 또는 일문으로 변환.
* **LLM 활용:** 고정된 템플릿 외의 동적 텍스트가 있을 경우, 사용자가 입력한 LLM API를 호출하여 구조를 깨뜨리지 않고(JSON 포맷 유지) 내용만 번역하여 덮어쓰기 수행. (한국어 컴플라이언스 프로파일 등 불필요한 파일 자동 삭제 포함).

### 3.6. 자동 실행 및 로그 모니터링 (LLM 통합)
* **설치 및 구동:** 터미널 백그라운드 프로세스로 구동 스크립트 실행.
* **지능형 오류 분석 (LLM 활용):**
  * 모니터링 대상: `ops/logs` (설치 단계) 및 `logs/[모듈명]` (실행 단계) 폴더 내 `.log` 파일.
  * 장애 발생 시: 프로세스가 `Exit 1` 등으로 실패하거나 로그 상에 `ERROR`, `FATAL` 발생 시, 해당 로그의 Tail(마지막 N줄)을 추출하여 LLM 프롬프트에 전송.
  * LLM이 분석한 **"오류 원인 및 조치 방법"**을 터미널에 사용자 친화적으로 출력.

## 4. 비기능 요구사항 (Non-Functional Requirements)
* **멱등성(Idempotency):** 에이전트를 여러 번 실행하더라도 설정 파일 패치가 중복으로 누적되지 않아야 함 (예: `install.locale`이 이미 존재하면 수정 건너뛰기).
* **UI/UX:** Antigravity 프레임워크의 Spinner 및 Progress Bar 컴포넌트를 사용하여 현재 진행 중인 단계(예: "Patching properties...", "Translating DB profiles...")를 명확히 시각화.
* **보안:** 터미널에 입력받은 LLM API Key는 메모리에만 임시 저장하며, 로컬 디스크나 로그 파일에 평문으로 남기지 않음.

## 5. 예외 처리 가이드 (Error Handling)
| 시나리오 | 동작 | 출력 가이드 |
| :--- | :--- | :--- |
| **관리자 권한 충돌 (Windows)** | 실행 즉시 중단 | "[ERROR] PostgreSQL 제약으로 인해 일반 사용자 권한으로 터미널을 다시 실행해 주세요." |
| **IP 추출 실패** | 실행 중단 | "[ERROR] 네트워크 IP를 식별할 수 없습니다. 연결 상태를 확인하세요." |
| **포트 기사용 중** | 실행 중단 | "[ERROR] 포트 {port_number}가 이미 사용 중입니다. 점유 중인 프로세스를 종료하세요." |
| **LLM API 키 인증 실패** | 재입력 프롬프트 | "[WARN] API Key가 유효하지 않습니다. 다시 입력해 주세요." |