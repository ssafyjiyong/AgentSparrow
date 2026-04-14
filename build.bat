@echo off
chcp 65001 > nul
echo.
echo ============================================================
echo   Sparrow Installation Agent - EXE 빌드
echo ============================================================
echo.

REM 가상환경 활성화 (있으면)
if exist ".venv\Scripts\activate.bat" (
    echo   >> 가상환경 활성화...
    call .venv\Scripts\activate.bat
)

REM 빌드 실행
python build.py

echo.
pause
