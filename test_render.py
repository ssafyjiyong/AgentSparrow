import ctypes
ctypes.windll.kernel32.SetConsoleOutputCP(65001)

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

console = Console(legacy_windows=False)

BANNER = r"""
   ____                                        ___                    __
  / __/ ___  ___ _ ____ ____ ___  _    __ _    / _ | ___ _ ___  ___  / /_
 _\  \  / _ \/ _ `// __// __// _ \| |/|/ // /  / __ |/ _ `// -_)/ _ \/ __/
/___/ / .__/\_,_//_/  /_/   \___/|__,__//_/  /_/ |_|\_,_/ \__//_//_/\__/
     /_/
"""

console.print(Panel(
    Text(BANNER, style="bold cyan")
    + Text(
        "\n  Sparrow Enterprise Server Installation Agent v1.0.0\n"
        "  Automated Installation Pipeline with LLM Intelligence\n",
        style="dim",
    ),
    border_style="bright_blue", padding=(0, 2),
))

console.print()
console.print(Rule("[bold bright_blue]STEP 1/6[/bold bright_blue]  사전 환경 점검", style="bright_blue"))
console.print()
console.print("  [bold]1-1. 실행 권한 검증[/bold]")
console.print("  [green][ OK ]  실행 권한 확인 완료 (일반 사용자)[/green]")
console.print()
console.print("  [bold]1-2. 포트 충돌 검사[/bold]")
console.print("  [green][ OK ]  포트 충돌 검사 완료 (23개 포트 모두 사용 가능)[/green]")
console.print()
console.print(Rule("[bold bright_blue]STEP 2/6[/bold bright_blue]  LLM 및 설치 설정", style="bright_blue"))
console.print()
console.print(Panel(
    "[bold]사용할 LLM 제공자를 선택하세요.[/bold]\n\n"
    "  [cyan]1[/cyan]  Gemini  (Google)\n"
    "  [cyan]2[/cyan]  GPT     (OpenAI)\n"
    "  [cyan]3[/cyan]  Claude  (Anthropic)",
    title="LLM 설정", border_style="bright_blue",
))
console.print("  [green][ OK ]  선택: GEMINI[/green]")
console.print()
console.print(Rule("[bold bright_blue]STEP 3/6[/bold bright_blue]  패키지 압축 해제", style="bright_blue"))
console.print("  [green][ OK ]  압축 해제 완료: C:\\Sparrow[/green]")
console.print("  [green][ OK ]  BASE_DIR : C:\\Sparrow\\sparrow-enterprise-server-windows-2603.2[/green]")
console.print()
console.print(Rule("[bold bright_blue]STEP 4/6[/bold bright_blue]  Properties 자동 구성", style="bright_blue"))
console.print("  [cyan] >>   service.host = 192.168.70.138[/cyan]")
console.print("  [cyan] >>   service.rasp.enabled = false[/cyan]")
console.print("  [green][ OK ]  sparrow.properties 패치 완료 (5개 항목 변경)[/green]")
console.print()
console.print(Rule("[bold bright_blue]STEP 5/6[/bold bright_blue]  DB 프로파일 다국어 패치", style="bright_blue"))
console.print("  [dim]  --   한국어(ko) 선택: DB 프로파일 번역을 건너뜁니다.[/dim]")
console.print()
console.print(Rule("[bold bright_blue]STEP 6/6[/bold bright_blue]  서비스 실행 및 헬스 체크", style="bright_blue"))
console.print("  [cyan] >>   구동 스크립트: start_server.bat[/cyan]")
console.print("  [bold green][ OK ]  서버 정상 구동 확인 (HTTP 200)[/bold green]")
console.print()
console.print(Panel(
    "[bold green]Sparrow Enterprise Server 설치가 완료되었습니다![/bold green]\n\n"
    "  설치 경로: C:\\Sparrow\\sparrow-enterprise-server-windows-2603.2\n"
    "  접속 주소: http://192.168.70.138:10880\n"
    "  언어 설정: ko\n"
    "  LLM 제공자: Google Gemini",
    title="설치 완료", border_style="green", padding=(1, 2),
))
