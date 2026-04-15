"""
대화형 CLI 입력 처리
- 언어 선택
- 선택적 모듈 선택 (sast / dast / sca)
- 패키지 경로 입력 (검증 포함)
- 설정 요약 및 최종 확인

LLM 제공자/API Key 입력은 설치 또는 구동 실패 시에만 지연 수집됩니다
(ensure_llm_client 참조).
"""
from pathlib import Path
from typing import Optional

from agent.config import AgentConfig, LLMProvider, Language, OPTIONAL_MODULES
from agent.llm.base import LLMClient, create_llm_client


def _ask(prompt: str, choices: list[str] | None = None, default: str | None = None) -> str:
    """choices가 있으면 유효한 선택지가 입력될 때까지 반복합니다."""
    if default:
        display = f"{prompt} (기본값: {default}): "
    else:
        display = f"{prompt}: "

    while True:
        ans = input(display).strip()
        if not ans and default is not None:
            return default
        if choices is None or ans.lower() in [c.lower() for c in choices]:
            return ans
        print(f"  [WARN] 올바른 값을 입력하세요: {', '.join(choices)}")


def _confirm(prompt: str, default: bool = True) -> bool:
    """Y/n 또는 y/N 입력을 받습니다."""
    default_str = "Y/n" if default else "y/N"
    while True:
        ans = input(f"  {prompt} [{default_str}]: ").strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  y 또는 n을 입력하세요.")


def _section(title: str):
    print()
    print("  " + "=" * 50)
    print(f"  {title}")
    print("  " + "=" * 50)


def collect_user_input(config: AgentConfig) -> bool:
    """
    사용자로부터 필요한 입력값을 순차적·대화식으로 수집합니다.

    Returns:
        True: 모든 입력 수집 + 최종 확인 완료
        False: 취소 또는 실패
    """
    print()

    # ── 1. 언어 선택 ──────────────────────────────────────────────────
    _section("[1/3] 언어 설정")
    print("  Sparrow 환경의 언어를 선택하세요.")
    print()
    print("  ko - 한국어 (기본)")
    print("  en - English")
    print("  ja - 日本語")
    print()

    lang_map = {
        "ko": Language.KO,
        "en": Language.EN,
        "ja": Language.JA,
    }

    choice = _ask("  언어 선택", choices=["ko", "en", "ja"], default="ko")
    config.language = lang_map[choice]
    lang_names = {"ko": "한국어", "en": "English", "ja": "日本語"}
    print(f"  [ OK ] 선택: {lang_names[choice]}")
    print()

    # ── 2. 선택적 모듈 선택 (sast / dast / sca) ───────────────────────
    _section("[2/3] 선택적 모듈")
    print("  활성화할 선택적 모듈을 선택하세요.")
    print("  (활성화하지 않은 모듈은 sparrow.properties에서 false로 설정됩니다.)")
    print()

    module_descriptions = {
        "sast": "SAST  (Static Application Security Testing)",
        "dast": "DAST  (Dynamic Application Security Testing)",
        "sca":  "SCA   (Software Composition Analysis)",
    }

    config.enabled_optional_modules = []
    for module in OPTIONAL_MODULES:
        desc = module_descriptions[module]
        if _confirm(f"{desc} 활성화?", default=True):
            config.enabled_optional_modules.append(module)
            print(f"  [ ON ] {module.upper()} 활성화")
        else:
            print(f"  [OFF] {module.upper()} 비활성화")

    print()

    # ── 3. 패키지 경로 입력 ─────────────────────────────────────────────
    _section("[3/3] 패키지 경로")
    print("  Sparrow Enterprise Server .zip 파일의 경로를 입력하세요.")
    print(r"  예) C:\Downloads\sparrow-enterprise-server-windows-2603.2.zip")
    print()

    while True:
        path_str = input("  파일 경로: ").strip().strip('"').strip("'")
        path = Path(path_str)

        if not path.exists():
            print(f"  [WARN] 파일이 존재하지 않습니다: {path}")
            continue

        if path.suffix.lower() != ".zip":
            print("  [WARN] .zip 파일만 지원합니다.")
            continue

        config.package_path = path.resolve()
        print(f"  [ OK ] 패키지 경로 확인: {config.package_path}")
        break

    print()

    # ── 설정 요약 및 최종 확인 ──────────────────────────────────────────
    _print_config_summary(config)

    if not _confirm("위 설정으로 설치를 시작하시겠습니까?", default=True):
        print("  설치가 취소되었습니다.")
        return False

    print()
    return True


def _print_config_summary(config: AgentConfig):
    print()
    print("  " + "=" * 50)
    print("  설정 요약")
    print("  " + "=" * 50)

    lang_names = {"ko": "한국어", "en": "English", "ja": "日本語"}
    modules_str = (
        ", ".join(m.upper() for m in config.enabled_optional_modules)
        if config.enabled_optional_modules
        else "없음 (모두 비활성화)"
    )

    print(f"  언어        : {lang_names.get(config.language.value, config.language.value)}")
    print(f"  선택 모듈   : {modules_str}")
    print(f"  패키지 경로 : {config.package_path}")
    print(f"  OS          : {config.os_type.value.upper()}")
    print("  " + "=" * 50)
    print()


def ensure_llm_client(config: AgentConfig, reason: str = "") -> Optional[LLMClient]:
    """
    LLM 클라이언트를 지연 초기화합니다.

    설치 실패/구동 실패 등 AI 분석이 필요한 순간에 호출됩니다.
    최초 호출 시 LLM 제공자와 API Key를 대화식으로 수집하며,
    이후 호출부터는 config.llm_client에 캐시된 클라이언트를 재사용합니다.

    Returns:
        LLMClient: 검증된 클라이언트
        None: 사용자가 입력을 포기했거나 검증에 최종 실패한 경우
    """
    if config.llm_client is not None:
        return config.llm_client  # type: ignore[return-value]

    print()
    print("  " + "=" * 60)
    print("  [AI] 로그 분석을 위해 LLM API Key가 필요합니다")
    if reason:
        print(f"        사유: {reason}")
    print("  " + "=" * 60)
    print()
    print("  사용할 LLM 제공자를 선택하세요.")
    print("  1 - Gemini  (Google)")
    print("  2 - GPT     (OpenAI)")
    print("  3 - Claude  (Anthropic)")
    print("  s - 건너뛰기 (AI 분석 없이 원시 로그만 출력)")
    print()

    provider_map = {
        "1": LLMProvider.GEMINI,
        "2": LLMProvider.GPT,
        "3": LLMProvider.CLAUDE,
        "gemini": LLMProvider.GEMINI,
        "gpt": LLMProvider.GPT,
        "claude": LLMProvider.CLAUDE,
    }

    choice = _ask(
        "  LLM 선택",
        choices=["1", "2", "3", "gemini", "gpt", "claude", "s", "skip"],
        default="1",
    ).lower()
    if choice in ("s", "skip"):
        print("  [SKIP] AI 분석을 건너뜁니다.")
        return None

    config.llm_provider = provider_map[choice]
    print(f"  [ OK ] 선택: {config.llm_provider.value.upper()}")
    print()
    print(f"  {config.llm_provider.value.upper()} API Key를 입력하세요.")
    print("  (API Key는 메모리에만 임시 저장되며, 로그 파일에 저장되지 않습니다.)")
    print()

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        api_key = input("  API Key: ").strip()
        if not api_key:
            print("  [WARN] API Key를 입력해 주세요.")
            continue

        config.api_key = api_key
        print("  >> API Key 검증 중...")
        try:
            client = create_llm_client(config.llm_provider, config.api_key)
            if client.validate_key():
                print("  [ OK ] API Key 검증 완료")
                config.llm_client = client
                return client
            remaining = max_retries - attempt
            if remaining > 0:
                print(f"  [WARN] API Key가 유효하지 않습니다. 다시 입력해 주세요. (남은 시도: {remaining})")
            else:
                print("  [FAIL] API Key 검증 실패.")
                return None
        except Exception as e:
            remaining = max_retries - attempt
            if remaining > 0:
                print(f"  [WARN] API Key 검증 오류: {e}")
                print(f"         다시 입력해 주세요. (남은 시도: {remaining})")
            else:
                print("  [FAIL] API Key 검증 실패.")
                return None

    return None
