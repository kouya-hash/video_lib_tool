@echo off
chcp 65001 > nul

set PYTHON=C:\Users\kouya\AppData\Local\Programs\Python\Python314\python.exe
set DEV_DIR=F:\kouya\dev\video_library_tool
set VENV=%DEV_DIR%\.venv

echo ============================================================
echo  Video Library Tool  -  開発環境セットアップ
echo  Python : %PYTHON%
echo  フォルダ: %DEV_DIR%
echo ============================================================
echo.

REM ── Python 確認 ──────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] Python が見つかりません:
    echo         %PYTHON%
    echo         パスを確認してください。
    pause & exit /b 1
)
echo [OK] Python が見つかりました
"%PYTHON%" --version
echo.

REM ── 開発フォルダ作成 ─────────────────────────────────────────
if not exist "%DEV_DIR%" (
    echo フォルダを作成します: %DEV_DIR%
    mkdir "%DEV_DIR%"
)
echo [OK] 開発フォルダ: %DEV_DIR%
echo.

REM ── ファイルをコピー ─────────────────────────────────────────
echo ── ファイルをコピー中 ───────────────────────────────────────
set SRC=%~dp0
copy /Y "%SRC%video_lib_tool.py"  "%DEV_DIR%\video_lib_tool.py"  > nul 2>&1 && echo [OK] video_lib_tool.py  || echo [SKIP] video_lib_tool.py (見つかりません)
copy /Y "%SRC%requirements.txt"   "%DEV_DIR%\requirements.txt"   > nul 2>&1 && echo [OK] requirements.txt   || echo [SKIP] requirements.txt
copy /Y "%SRC%build.bat"          "%DEV_DIR%\build.bat"          > nul 2>&1 && echo [OK] build.bat          || echo [SKIP] build.bat
echo.

REM ── 仮想環境 (venv) を作成 ────────────────────────────────────
if not exist "%VENV%\Scripts\python.exe" (
    echo ── 仮想環境を作成中...
    "%PYTHON%" -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] 仮想環境の作成に失敗しました。
        pause & exit /b 1
    )
    echo [OK] 仮想環境を作成しました: %VENV%
) else (
    echo [OK] 仮想環境は既に存在します: %VENV%
)
echo.

REM ── PySide6 インストール ──────────────────────────────────────
echo ── PySide6 をインストール中（初回は数分かかります）──────────
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%VENV%\Scripts\python.exe" -m pip install PySide6
if errorlevel 1 (
    echo [ERROR] PySide6 のインストールに失敗しました。
    pause & exit /b 1
)
echo [OK] PySide6 インストール完了
echo.

REM ── 起動スクリプトを生成 ─────────────────────────────────────
(
    echo @echo off
    echo chcp 65001 ^> nul
    echo "%VENV%\Scripts\python.exe" "%DEV_DIR%\video_lib_tool.py"
    echo if errorlevel 1 pause
) > "%DEV_DIR%\run_dev.bat"
echo [OK] 起動スクリプト生成: %DEV_DIR%\run_dev.bat
echo.

echo ============================================================
echo  セットアップ完了！
echo.
echo  次のステップ:
echo    1. %DEV_DIR% を開く
echo    2. run_dev.bat をダブルクリックでツール起動
echo ============================================================
echo.
start explorer "%DEV_DIR%"
pause
