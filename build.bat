REM ============================================================
REM build.bat
REM 
REM Beschrijving: Build script voor Windows executable
REM Applicatie: networkmanager
REM Versie: 1.0.0
REM Auteur: Barremans
REM ============================================================

@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

rem ================================================
rem networkmanager - Build Script
rem Versie: Dynamisch uit app/version.py
rem ================================================

echo.
echo ========================================
echo  networkmanager - Build Script
echo ========================================
echo.

rem Altijd uitvoeren vanuit de map waar dit .bat bestand staat
cd /d "%~dp0"

rem ---- Config ----
set "PROJECT_NAME=networkmanager"
set "SPEC_FILE=networkmanager.spec"
set "DST_FOLDER=dist"

rem ---- Python detectie ----
set "PYEXE="
if exist "venv\Scripts\python.exe" set "PYEXE=venv\Scripts\python.exe"
if not defined PYEXE if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"

echo [INFO] Python: %PYEXE%
"%PYEXE%" --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Python niet gevonden!
    echo.
    echo Zorg dat Python geinstalleerd is of activeer venv:
    echo   venv\Scripts\activate
    echo.
    pause
    exit /b 1
)
echo [OK] Python gevonden
echo.

rem ---- Versie verhogen? ----
set /p DO_BUMP=Wil je de versie verhogen? [J/N] : 
if /I "%DO_BUMP%"=="J" (
    echo.
    set /p PART_TO_BUMP=Welke versie? (patch/minor/major) [patch] : 
    if "!PART_TO_BUMP!"=="" set "PART_TO_BUMP=patch"
    
    echo [1] Versie verhogen...
    cd scripts
    "%PYEXE%" bump_version.py !PART_TO_BUMP!
    if errorlevel 1 (
        echo ❌ Versie bump faalde
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [OK] Versie verhoogd
)
echo.

rem ---- Versie lezen ----
echo [2] Versie lezen uit app/version.py...

set "PY_READV=%TEMP%\__read_version.py"
set "VER_TXT=%TEMP%\__version_out.txt"

> "%PY_READV%" echo import re, io
>>"%PY_READV%" echo with io.open('app/version.py', 'r', encoding='utf-8') as f:
>>"%PY_READV%" echo     content = f.read()
>>"%PY_READV%" echo m = re.search(r"__version__\s*=\s*[\"']([0-9.]+)", content)
>>"%PY_READV%" echo v = m.group(1) if m else "0.0.0"
>>"%PY_READV%" echo with io.open(r'%VER_TXT%', 'w', encoding='utf-8') as f:
>>"%PY_READV%" echo     f.write(v)

"%PYEXE%" "%PY_READV%"
if errorlevel 1 (
    echo ❌ Kon versie niet lezen
    pause
    exit /b 1
)

set "APP_VERSION="
set /p APP_VERSION=<"%VER_TXT%"
del /q "%PY_READV%" "%VER_TXT%" >nul 2>&1

if not defined APP_VERSION (
    echo ❌ Geen versie gevonden
    pause
    exit /b 1
)

echo [OK] Versie: %APP_VERSION%
echo.

rem ---- Opschonen ----
echo [3] Opschonen...
if exist build rmdir /s /q build >nul 2>&1
if exist "%DST_FOLDER%" rmdir /s /q "%DST_FOLDER%" >nul 2>&1
echo [OK] Opgeruimd
echo.

rem ---- Dependencies ----
echo [4] Dependencies...
"%PYEXE%" -m pip install --upgrade pip --quiet

if exist requirements.txt (
    "%PYEXE%" -m pip install -r requirements.txt --quiet
)

rem PyInstaller check
"%PYEXE%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [4a] PyInstaller installeren...
    "%PYEXE%" -m pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller installatie faalde
        pause
        exit /b 1
    )
)
echo [OK] Dependencies OK
echo.

rem ---- .spec bestand maken indien niet aanwezig ----
if not exist "%SPEC_FILE%" (
    echo [5] .spec bestand aanmaken...
    
    "%PYEXE%" -c "import sys; print(sys.executable)" > "%TEMP%\pypath.txt"
    set /p PYTHON_PATH=<"%TEMP%\pypath.txt"
    del /q "%TEMP%\pypath.txt"
    
    > "%SPEC_FILE%" echo # -*- mode: python ; coding: utf-8 -*-
    >>"%SPEC_FILE%" echo.
    >>"%SPEC_FILE%" echo block_cipher = None
    >>"%SPEC_FILE%" echo.
    >>"%SPEC_FILE%" echo a = Analysis(
    >>"%SPEC_FILE%" echo     ['app/main.py'],
    >>"%SPEC_FILE%" echo     pathex=[],
    >>"%SPEC_FILE%" echo     binaries=[],
    >>"%SPEC_FILE%" echo     datas=[
    >>"%SPEC_FILE%" echo         ('assets', 'assets'),
    >>"%SPEC_FILE%" echo         ('config', 'config'),
    >>"%SPEC_FILE%" echo         ('css', 'css'),
    >>"%SPEC_FILE%" echo         ('i18n/locales/*.json', 'i18n/locales'),
    >>"%SPEC_FILE%" echo     ],
    >>"%SPEC_FILE%" echo     hiddenimports=[],
    >>"%SPEC_FILE%" echo     hookspath=[],
    >>"%SPEC_FILE%" echo     hooksconfig={},
    >>"%SPEC_FILE%" echo     runtime_hooks=[],
    >>"%SPEC_FILE%" echo     excludes=[],
    >>"%SPEC_FILE%" echo     win_no_prefer_redirects=False,
    >>"%SPEC_FILE%" echo     win_private_assemblies=False,
    >>"%SPEC_FILE%" echo     cipher=block_cipher,
    >>"%SPEC_FILE%" echo     noarchive=False,
    >>"%SPEC_FILE%" echo ^)
    >>"%SPEC_FILE%" echo.
    >>"%SPEC_FILE%" echo pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher^)
    >>"%SPEC_FILE%" echo.
    >>"%SPEC_FILE%" echo exe = EXE(
    >>"%SPEC_FILE%" echo     pyz,
    >>"%SPEC_FILE%" echo     a.scripts,
    >>"%SPEC_FILE%" echo     a.binaries,
    >>"%SPEC_FILE%" echo     a.zipfiles,
    >>"%SPEC_FILE%" echo     a.datas,
    >>"%SPEC_FILE%" echo     [],
    >>"%SPEC_FILE%" echo     name='%PROJECT_NAME%',
    >>"%SPEC_FILE%" echo     debug=False,
    >>"%SPEC_FILE%" echo     bootloader_ignore_signals=False,
    >>"%SPEC_FILE%" echo     strip=False,
    >>"%SPEC_FILE%" echo     upx=True,
    >>"%SPEC_FILE%" echo     upx_exclude=[],
    >>"%SPEC_FILE%" echo     runtime_tmpdir=None,
    >>"%SPEC_FILE%" echo     console=False,
    >>"%SPEC_FILE%" echo     disable_windowed_traceback=False,
    >>"%SPEC_FILE%" echo     argv_emulation=False,
    >>"%SPEC_FILE%" echo     target_arch=None,
    >>"%SPEC_FILE%" echo     codesign_identity=None,
    >>"%SPEC_FILE%" echo     entitlements_file=None,
    >>"%SPEC_FILE%" echo ^)
    
    echo [OK] .spec bestand aangemaakt
    echo.
)

rem ---- PyInstaller Build ----
echo [5] PyInstaller build...
echo Dit kan enkele minuten duren...
echo.

"%PYEXE%" -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Build faalde!
    echo.
    pause
    exit /b 1
)

if not exist "%DST_FOLDER%\%PROJECT_NAME%\%PROJECT_NAME%.exe" (
    echo.
    echo ❌ ERROR: .exe niet gevonden
    echo.
    pause
    exit /b 1
)

echo [OK] Build succesvol!
echo.

rem ---- Hernoemen met versie ----
echo [6] Folder hernoemen...

set "BUILD_FOLDER=%PROJECT_NAME%_%APP_VERSION%"

if exist "%DST_FOLDER%\%BUILD_FOLDER%" rmdir /s /q "%DST_FOLDER%\%BUILD_FOLDER%" >nul 2>&1

rename "%DST_FOLDER%\%PROJECT_NAME%" "%BUILD_FOLDER%" >nul 2>&1
if errorlevel 1 (
    robocopy "%DST_FOLDER%\%PROJECT_NAME%" "%DST_FOLDER%\%BUILD_FOLDER%" /E /MOVE /NFL /NDL /NJH /NJS >nul
    if errorlevel 8 (
        echo ❌ Hernoemen faalde
        pause
        exit /b 1
    )
)

echo [OK] Folder: %BUILD_FOLDER%
echo.

rem ---- Version.txt ----
> "%DST_FOLDER%\%BUILD_FOLDER%\version.txt" echo %APP_VERSION%

rem ---- Resultaat ----
echo.
echo ========================================
echo  BUILD SUCCESVOL!
echo ========================================
echo.
echo 📌 Versie: %APP_VERSION%
echo 📂 Folder: %DST_FOLDER%\%BUILD_FOLDER%
echo 💻 EXE: %DST_FOLDER%\%BUILD_FOLDER%\%PROJECT_NAME%.exe
echo.
echo ✅ Klaar om te testen!
echo.

set /p OPEN_FOLDER=Output folder openen? [J/N] : 
if /I "%OPEN_FOLDER%"=="J" explorer "%DST_FOLDER%\%BUILD_FOLDER%"

pause
endlocal
