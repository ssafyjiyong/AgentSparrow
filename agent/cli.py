"""
대화형 CLI 입력 처리
- LLM 제공자 선택
- API Key 입력
- 언어 선택
- 선택적 모듈 선택 (sast / dast / sca)
- 패키지 경로 입력 (검증 포함)
- 설정 요약 및 최종 확인
"""
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.rule import Rule

from agent.config import AgentConfig, LLMProvider, Language, OPTIONAL_MODULES

console = Console(force_terminal=True, legacy_windows=False)


def collect_user_input(config: AgentConfig) -> bool:
    """
    사용자로부터 필요한 입력값을 순차적·대화식으로 수집합니다.

    Args:
        config: 설정 객체 (수집된 값으로 채워짐)

    Returns:
        True: 모든 입력 수집 + 최종 확인 완료
        False: 취소 또는 실패
    """
    console.print()

    # ── 1. LLM 제공자 선택 ──────────────────────────────────────────────
    console.print(Panel(
        "[bold]사용할 LLM 제공자를 선택하세요.[/bold]\n\n"
        "  [cyan]1[/cyan] │ Gemini  (Google)\n"
        "  [cyan]2[/cyan] │ GPT     (OpenAI)\n"
        "  [cyan]3[/cyan] │ Claude  (Anthropic)",
        title="[1/5] LLM 설정",
        border_style="bright_blue",
    ))

    provider_map = {
        "1": LLMProvider.GEMINI,
        "2": LLMProvider.GPT,
        "3": LLMProvider.CLAUDE,
        "gemini": LLMProvider.GEMINI,
        "gpt": LLMProvider.GPT,
        "claude": LLMProvider.CLAUDE,
    }

    choice = Prompt.ask(
        "  LLM 선택",
        choices=["1", "2", "3", "gemini", "gpt", "claude"],
        default="1",
    )
    config.llm_provider = provider_map[choice.lower()]
    console.print(
        f"  [ OK ] 선택: {config.llm_provider.value.upper()}",
        style="green",
    )
    console.print()

    # ── 2. API Key 입력 ──────────────────────────────────────────────────
    console.print(Panel(
        f"[bold]{config.llm_provider.value.upper()} API Key를 입력하세요.[/bold]\n"
        "[dim]API Key는 메모리에만 임시 저장되며, 로그 파일에 저장되지 않습니다.[/dim]",
        title="[2/5] API Key",
        border_style="bright_blue",
    ))

    from agent.llm.base import create_llm_client

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        api_key = Prompt.ask("  API Key")

        if not api_key.strip():
            console.print("  [WARN] API Key를 입력해 주세요.", style="yellow")
            continue

        config.api_key = api_key.strip()

        # API Key 유효성 검증
        console.print("  >> API Key 검증 중...", style="dim")
        try:
            client = create_llm_client(config.llm_provider, config.api_key)
            if client.validate_key():
                console.print("  [ OK ] API Key 검증 완료", style="green")
                break
            else:
                remaining = max_retries - attempt
                if remaining > 0:
                    console.print(
                        f"  [WARN] API Key가 유효하지 않습니다. "
                        f"다시 입력해 주세요. (남은 시도: {remaining})",
                        style="yellow",
                    )
                else:
                    console.print(
                        "  [FAIL] API Key 검증 실패. 프로그램을 종료합니다.",
                        style="red",
                    )
                    return False
        except Exception as e:
            remaining = max_retries - attempt
            if remaining > 0:
                console.print(
                    f"  [WARN] API Key 검증 오류: {e}\n"
                    f"  다시 입력해 주세요. (남은 시도: {remaining})",
                    style="yellow",
                )
            else:
                console.print(
                    "  [FAIL] API Key 검증 실패. 프로그램을 종료합니다.",
                    style="red",
                )
                return False

    console.print()

    # ── 3. 언어 선택 ──────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Sparrow 환경의 언어를 선택하세요.[/bold]\n\n"
        "  [cyan]ko[/cyan] │ 한국어 (기본)\n"
        "  [cyan]en[/cyan] │ English\n"
        "  [cyan]ja[/cyan] │ 日本語",
        title="[3/5] 언어 설정",
        border_style="bright_blue",
    ))

    lang_map = {
        "ko": Language.KO,
        "en": Language.EN,
        "ja": Language.JA,
    }

    choice = Prompt.ask(
        "  언어 선택",
        choices=["ko", "en", "ja"],
        default="ko",
    )
    config.language = lang_map[choice]
    lang_names = {"ko": "한국어", "en": "English", "ja": "日本語"}
    console.print(
        f"  [ OK ] 선택: {lang_names[choice]}",
        style="green",
    )
    console.print()

    # ── 4. 선택적 모듈 선택 (sast / dast / sca) ───────────────────────
    console.print(Panel(
        "[bold]활성화할 선택적 모듈을 선택하세요.[/bold]\n"
        "[dim]각 모듈은 독립적으로 활성화/비활성화할 수 있습니다.\n"
        "활성화하지 않은 모듈은 sparrow.properties에서 false로 설정됩니다.[/dim]",
        title="[4/5] 선택적 모듈",
        border_style="bright_blue",
    ))

    module_descriptions = {
        "sast": "SAST  (Static Application Security Testing)",
        "dast": "DAST  (Dynamic Application Security Testing)",
        "sca":  "SCA   (Software Composition Analysis)",
    }

    config.enabled_optional_modules = []
    for module in OPTIONAL_MODULES:
        desc = module_descriptions[module]
        enabled = Confirm.ask(f"  {desc} 활성화?", default=False)
        if enabled:
            config.enabled_optional_modules.append(module)
            console.print(f"  [ ON ] {module.upper()} 활성화", style="green")
        else:
            console.print(f"  [OFF] {module.upper()} 비활성화", style="dim")

    console.print()

    # ── 5. 패키지 경로 입력 ─────────────────────────────────────────────
    console.print(Panel(
        "[bold]Sparrow Enterprise Server .zip 파일의 경로를 입력하세요.[/bold]\n"
        "[dim]예: C:\\Downloads\\sparrow-enterprise-server-windows-2603.2.zip[/dim]",
        title="[5/5] 패키지 경로",
        border_style="bright_blue",
    ))

    while True:
        path_str = Prompt.ask("  파일 경로")
        path = Path(path_str.strip().strip('"').strip("'"))

        if not path.exists():
            console.print(
                f"  [WARN] 파일이 존재하지 않습니다: {path}",
                style="yellow",
            )
            continue

        if not path.suffix.lower() == ".zip":
            console.print(
                "  [WARN] .zip 파일만 지원합니다.",
                style="yellow",
            )
            continue

        config.package_path = path.resolve()
        console.print(
            f"  [ OK ] 패키지 경로 확인: {config.package_path}",
            style="green",
        )
        break

    console.print()

    # ── 설정 요약 및 최종 확인 ──────────────────────────────────────────
    _print_config_summary(config)

    if not Confirm.ask("  위 설정으로 설치를 시작하시겠습니까?", default=True):
        console.print("  설치가 취소되었습니다.", style="yellow")
        return False

    console.print()
    return True


def _print_config_summary(config: AgentConfig):
    """수집된 설정값을 요약 테이블로 출력합니다."""
    console.print(Rule("[bold]설정 요약[/bold]", style="bright_blue"))
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("항목", style="dim", min_width=20)
    table.add_column("값", style="bold")

    lang_names = {"ko": "한국어", "en": "English", "ja": "日本語"}
    modules_str = (
        ", ".join(m.upper() for m in config.enabled_optional_modules)
        if config.enabled_optional_modules
        else "없음 (모두 비활성화)"
    )

    table.add_row("LLM 제공자", config.llm_provider.value.upper())
    table.add_row("언어", lang_names.get(config.language.value, config.language.value))
    table.add_row("선택 모듈", modules_str)
    table.add_row("패키지 경로", str(config.package_path))
    table.add_row("OS", config.os_type.value.upper())

    console.print(table)
    console.print()
