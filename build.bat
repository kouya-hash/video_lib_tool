@echo off
chcp 65001 > nul
echo ============================================================
echo  Video Library Tool  -  .exe ビルドスクリプト
echo ============================================================
echo.

REM ── Python 確認 ──────────────────────────────────────────────
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。
    echo         https://www.python.org/downloads/ からインストールして
    echo         「Add Python to PATH」にチェックを入れてください。
    pause
    exit /b 1
)
echo [OK] Python が見つかりました。
python --version

echo.
echo ── 必要なライブラリをインストール中 ─────────────────────────
pip install PySide6 pyinstaller
if errorlevel 1 (
    echo [ERROR] インストールに失敗しました。
    pause
    exit /b 1
)
echo [OK] インストール完了
echo.

REM ── ビルド ────────────────────────────────────────────────────
echo ── ビルド中（数分かかります）────────────────────────────────
pyinstaller ^
    --onedir ^
    --windowed ^
    --name "VideoLibraryTool" ^
    --clean ^
    video_lib_tool.py

if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上記のエラーを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完了！
echo  dist\VideoLibraryTool\ フォルダが作成されました。
echo  このフォルダごとサーバーに置いて共有してください。
echo  起動は VideoLibraryTool.exe をダブルクリックするだけです。
echo ============================================================
echo.
pause
