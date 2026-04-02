@echo off
chcp 65001 > nul

set PYTHON=C:\Users\kouya\AppData\Local\Programs\Python\Python314\python.exe
set DEV_DIR=F:\kouya\dev\video_library_tool
set VENV=%DEV_DIR%\.venv

echo ============================================================
echo  Video Library Tool  -  .exe ビルドスクリプト
echo ============================================================
echo.

REM ── Python / venv 確認 ───────────────────────────────────────
if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] 仮想環境が見つかりません。
    echo         先に setup_dev.bat を実行してください。
    pause & exit /b 1
)
echo [OK] 仮想環境: %VENV%
echo.

REM ── PyInstaller インストール ──────────────────────────────────
echo ── PyInstaller をインストール中...
"%VENV%\Scripts\python.exe" -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] PyInstaller のインストールに失敗しました。
    pause & exit /b 1
)
echo [OK] PyInstaller 準備完了
echo.

REM ── ビルド ────────────────────────────────────────────────────
echo ── ビルド中（数分かかります）────────────────────────────────
cd /d "%DEV_DIR%"
"%VENV%\Scripts\python.exe" -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "VideoLibraryTool" ^
    --clean ^
    "%DEV_DIR%\video_lib_tool.py"

if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上記のエラーを確認してください。
    pause & exit /b 1
)

echo.
echo ============================================================
echo  完了！
echo  %DEV_DIR%\dist\VideoLibraryTool\VideoLibraryTool.exe
echo  このフォルダごとサーバーに置いて共有できます。
echo ============================================================
echo.
start explorer "%DEV_DIR%\dist\VideoLibraryTool"
pause
