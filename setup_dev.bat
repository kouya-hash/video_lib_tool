@echo off
chcp 65001 > nul
echo ============================================================
echo  Video Library Tool  -  開発環境セットアップ
echo  対象フォルダ: F:\kouya\dev\video_library_tool
echo ============================================================
echo.

set DEV_DIR=F:\kouya\dev\video_library_tool

REM ── Python を探す ────────────────────────────────────────────
set PYTHON=

python --version > nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :found )

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set PYTHON=%%D\python.exe & goto :found )
)
for /d %%D in ("%PROGRAMFILES%\Python3*") do (
    if exist "%%D\python.exe" ( set PYTHON=%%D\python.exe & goto :found )
)

echo [ERROR] Python が見つかりません。
pause & exit /b 1

:found
echo [OK] Python: %PYTHON%
"%PYTHON%" --version
echo.

REM ── 開発フォルダ作成 ─────────────────────────────────────────
if not exist "%DEV_DIR%" (
    echo フォルダを作成: %DEV_DIR%
    mkdir "%DEV_DIR%"
)

REM ── ファイルをコピー ─────────────────────────────────────────
echo ── ファイルをコピー中 ───────────────────────────────────────
set SRC=%~dp0

if exist "%SRC%video_lib_tool.py" (
    copy /Y "%SRC%video_lib_tool.py" "%DEV_DIR%\video_lib_tool.py" > nul
    echo [OK] video_lib_tool.py
)
if exist "%SRC%requirements.txt" (
    copy /Y "%SRC%requirements.txt" "%DEV_DIR%\requirements.txt" > nul
    echo [OK] requirements.txt
)
if exist "%SRC%build.bat" (
    copy /Y "%SRC%build.bat" "%DEV_DIR%\build.bat" > nul
    echo [OK] build.bat
)
echo.

REM ── 仮想環境 (venv) を作成 ────────────────────────────────────
set VENV=%DEV_DIR%\.venv
if not exist "%VENV%\Scripts\python.exe" (
    echo ── 仮想環境を作成中: %VENV%
    "%PYTHON%" -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] 仮想環境の作成に失敗しました。
        pause & exit /b 1
    )
    echo [OK] 仮想環境を作成しました
) else (
    echo [OK] 仮想環境は既に存在します: %VENV%
)
echo.

REM ── 依存ライブラリをインストール ─────────────────────────────
echo ── ライブラリをインストール中 ───────────────────────────────
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%VENV%\Scripts\pip.exe" install PySide6
if errorlevel 1 (
    echo [ERROR] PySide6 のインストールに失敗しました。
    pause & exit /b 1
)
echo [OK] PySide6 インストール完了
echo.

REM ── 起動スクリプトを生成 ─────────────────────────────────────
set LAUNCHER=%DEV_DIR%\run_dev.bat
(
    echo @echo off
    echo chcp 65001 ^> nul
    echo "%VENV%\Scripts\python.exe" "%DEV_DIR%\video_lib_tool.py"
    echo pause
) > "%LAUNCHER%"
echo [OK] 起動スクリプト生成: %LAUNCHER%
echo.

echo ============================================================
echo  セットアップ完了！
echo.
echo  開発フォルダ : %DEV_DIR%
echo  起動方法     : run_dev.bat をダブルクリック
echo  .exe ビルド  : build.bat をダブルクリック
echo ============================================================
echo.
pause
