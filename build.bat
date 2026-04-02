@echo off
chcp 65001 > nul
echo ============================================================
echo  Video Library Tool  -  .exe ビルドスクリプト
echo ============================================================
echo.

REM ── Python を探す ────────────────────────────────────────────
set PYTHON=

REM 1. PATH に通っている場合
python --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :found
)

REM 2. AppData (ユーザーインストール) を自動探索
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set PYTHON=%%D\python.exe
        goto :found
    )
)

REM 3. Program Files (全ユーザーインストール) を自動探索
for /d %%D in ("%PROGRAMFILES%\Python3*") do (
    if exist "%%D\python.exe" (
        set PYTHON=%%D\python.exe
        goto :found
    )
)

echo [ERROR] Python が見つかりません。
echo         https://www.python.org/downloads/ からインストールして
echo         「Add Python to PATH」にチェックを入れてください。
pause
exit /b 1

:found
echo [OK] Python が見つかりました: %PYTHON%
"%PYTHON%" --version
echo.

REM ── pip / pyinstaller / PySide6 インストール ─────────────────
echo ── 必要なライブラリをインストール中 ─────────────────────────
"%PYTHON%" -m pip install --upgrade pip
"%PYTHON%" -m pip install PySide6 pyinstaller
if errorlevel 1 (
    echo [ERROR] インストールに失敗しました。
    pause
    exit /b 1
)
echo [OK] インストール完了
echo.

REM ── ビルド ────────────────────────────────────────────────────
echo ── ビルド中（数分かかります）────────────────────────────────

REM このバッチファイルと同じフォルダにある video_lib_tool.py をビルド
set SCRIPT_DIR=%~dp0
"%PYTHON%" -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "VideoLibraryTool" ^
    --clean ^
    "%SCRIPT_DIR%video_lib_tool.py"

if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上記のエラーを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完了！
echo.
echo  dist\VideoLibraryTool\ フォルダが作成されました。
echo  このフォルダごとサーバーに置いて共有してください。
echo  起動は VideoLibraryTool.exe をダブルクリックするだけです。
echo ============================================================
echo.
pause
