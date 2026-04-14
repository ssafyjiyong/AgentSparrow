"""
PyInstaller 빌드 스크립트
- 단일 실행 파일(.exe / binary) 생성
- 더블클릭으로 바로 실행 가능

사용법:
    python build.py

출력:
    dist/sparrow-agent.exe  (Windows)
    dist/sparrow-agent      (Linux)
"""
import subprocess
import sys
import platform
from pathlib import Path


def ensure_pyinstaller():
    """PyInstaller가 설치되어 있지 않으면 자동 설치합니다."""
    try:
        import PyInstaller  # noqa: F401
        print("  [OK] PyInstaller 설치 확인")
    except ImportError:
        print("  >> PyInstaller 설치 중...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            capture_output=False,
        )
        if result.returncode != 0:
            print("  [FAIL] PyInstaller 설치 실패")
            sys.exit(1)
        print("  [OK] PyInstaller 설치 완료")


def build():
    """PyInstaller를 사용하여 단일 실행 파일을 빌드합니다."""
    project_root = Path(__file__).parent
    main_script = project_root / "main.py"

    if not main_script.exists():
        print(f"  [FAIL] {main_script} not found")
        sys.exit(1)

    system = platform.system()
    name = "sparrow-agent"

    print("=" * 60)
    print("  Sparrow Installation Agent - 빌드 시작")
    print(f"  OS: {system}")
    print(f"  출력: dist/{name}.exe" if system == "Windows" else f"  출력: dist/{name}")
    print("=" * 60)
    print()

    ensure_pyinstaller()
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",              # 단일 파일로 묶기
        "--console",              # 콘솔 창 표시 (CLI 앱이므로 필수)
        "--name", name,
        "--clean",                # 이전 빌드 캐시 제거
        "--noconfirm",            # 덮어쓰기 확인 없이 진행

        # ── google-genai (Gemini SDK) ──
        "--collect-all", "google.genai",
        "--collect-all", "google.ai",
        "--hidden-import", "google.genai",
        "--hidden-import", "google.genai.types",

        # ── OpenAI ──
        "--collect-all", "openai",
        "--hidden-import", "openai",

        # ── Anthropic ──
        "--collect-all", "anthropic",
        "--hidden-import", "anthropic",

        # ── Rich (터미널 UI) ──
        "--collect-all", "rich",
        "--hidden-import", "rich.console",
        "--hidden-import", "rich.panel",
        "--hidden-import", "rich.prompt",
        "--hidden-import", "rich.progress",
        "--hidden-import", "rich.rule",
        "--hidden-import", "rich.table",
        "--hidden-import", "rich.text",
        "--hidden-import", "rich.markdown",

        # ── requests ──
        "--hidden-import", "requests",

        # ── agent 패키지 ──
        "--hidden-import", "agent",
        "--hidden-import", "agent.config",
        "--hidden-import", "agent.cli",
        "--hidden-import", "agent.checks",
        "--hidden-import", "agent.checks.permissions",
        "--hidden-import", "agent.checks.ports",
        "--hidden-import", "agent.checks.packages",
        "--hidden-import", "agent.installer",
        "--hidden-import", "agent.installer.extractor",
        "--hidden-import", "agent.installer.properties",
        "--hidden-import", "agent.installer.profiles",
        "--hidden-import", "agent.installer.runner",
        "--hidden-import", "agent.llm",
        "--hidden-import", "agent.llm.base",
        "--hidden-import", "agent.llm.gemini",
        "--hidden-import", "agent.llm.openai_client",
        "--hidden-import", "agent.llm.claude",
        "--hidden-import", "agent.llm.prompts",
        "--hidden-import", "agent.utils",
        "--hidden-import", "agent.utils.network",
        "--hidden-import", "agent.utils.platform_utils",

        str(main_script),
    ]

    print("  >> PyInstaller 실행 중... (첫 빌드는 1~3분 소요)")
    print()

    result = subprocess.run(cmd, cwd=str(project_root))

    print()
    if result.returncode == 0:
        dist_dir = project_root / "dist"
        exe_path = dist_dir / (f"{name}.exe" if system == "Windows" else name)

        print("=" * 60)
        print("  [OK] 빌드 성공!")
        print(f"  출력 파일: {exe_path}")
        print()
        if system == "Windows":
            print("  실행 방법:")
            print(f"    - 더블클릭: {exe_path.name}")
            print(f"    - 터미널:   .\\dist\\{exe_path.name}")
        else:
            print("  실행 방법:")
            print(f"    - 터미널: ./dist/{name}")
        print("=" * 60)
    else:
        print("=" * 60)
        print(f"  [FAIL] 빌드 실패 (exit code: {result.returncode})")
        print("=" * 60)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
