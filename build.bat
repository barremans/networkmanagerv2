@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

rem Altijd uitvoeren vanuit de map waar dit .bat bestand staat
cd /d "%~dp0"

rem ================================================
rem build.bat — Networkmap_Creator
rem Stappen:
rem   1. Python/.venv detecteren
rem   2. Versie verhogen via bump_version.py
rem   3. Versie uitlezen uit app/version.py
rem   4. pip + vereisten installeren
rem   5. PyInstaller bouwen via networkmap.spec
rem   6. Map hernoemen naar versie
rem   7. Assets kopiëren
rem   8. Inno Setup installer compileren
rem ================================================

set "PROJECT_NAME=Networkmap_Creator"
set "SPEC_FILE=networkmap.spec"
set "DST_FOLDER=dist"
set "LOGFILE=build_log.txt"
set "VERSION_FILE=app\version.py"
set "ISS_FILE=installer\networkmap_setup.iss"

rem ---- Python uit .venv prefereren ----
set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE if exist "Scripts\python.exe" set "PYEXE=Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"

for %%I in ("%PYEXE%") do (
  if exist "%%~fI" set "PYEXE=%%~fI"
)

echo [info] Python: %PYEXE%
"%PYEXE%" -V >nul 2>&1 || (echo ❌ Geen werkende Python gevonden.& pause & exit /b 1)

rem ================================================
rem [0] Versie verhogen via bump_version.py
rem ================================================
set /p PART_TO_BUMP=Welke versie wil je verhogen? (patch/minor/major) [patch]: 
if "%PART_TO_BUMP%"=="" set "PART_TO_BUMP=patch"
echo [0] 🔁 Versie verhogen via bump_version.py (%PART_TO_BUMP%)...
"%PYEXE%" bump_version.py %PART_TO_BUMP% || (echo ❌ Versieverhoging mislukt.& pause & exit /b 1)

rem ================================================
rem [1] Versie robuust uitlezen uit app/version.py
rem ================================================
set "PY_READV=%TEMP%\__read_version_nm.py"
set "VER_TXT=%TEMP%\__version_nm_out.txt"
del /q "%PY_READV%" "%VER_TXT%" >nul 2>&1

> "%PY_READV%" echo import importlib.util, io, os, re
>>"%PY_READV%" echo p=os.path.abspath('app/version.py'); v="0.0.0"
>>"%PY_READV%" echo try:
>>"%PY_READV%" echo ^    spec=importlib.util.spec_from_file_location("ver",p)
>>"%PY_READV%" echo ^    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
>>"%PY_READV%" echo ^    v=str(getattr(m,"__version__","0.0.0"))
>>"%PY_READV%" echo except Exception:
>>"%PY_READV%" echo ^    t=io.open(p,'r',encoding='utf-8').read()
>>"%PY_READV%" echo ^    mm=re.search(r"__version__\s*=\s*['\"\s]*([0-9]+(?:\.[0-9]+){1,2})",t)
>>"%PY_READV%" echo ^    v=mm.group(1) if mm else "0.0.0"
>>"%PY_READV%" echo io.open(r'%VER_TXT%','w',encoding='utf-8').write(v.strip())

"%PYEXE%" "%PY_READV%" || (echo ❌ Versie uitlezen faalde.& del /q "%PY_READV%" >nul & pause & exit /b 1)
del /q "%PY_READV%" >nul 2>&1
set "NEW_VERSION=" & set /p NEW_VERSION=<"%VER_TXT%"
del /q "%VER_TXT%" >nul 2>&1
if not defined NEW_VERSION (echo ❌ Kon versie niet lezen uit %VERSION_FILE%.& pause & exit /b 1)
echo [1] 🔎 Versie: %NEW_VERSION%

rem ---- Afgeleide paden ----
set "BUILD_FOLDER=%PROJECT_NAME%_%NEW_VERSION%"
set "ABS_BUILD_FOLDER=%CD%\%DST_FOLDER%\%BUILD_FOLDER%"
set "INITIAL_EXE=%DST_FOLDER%\%PROJECT_NAME%\%PROJECT_NAME%.exe"

rem ================================================
rem [2] Opschonen
rem ================================================
echo [2] 🧹 Opruimen (build + dist)...
rmdir /s /q build 2>nul
rmdir /s /q "%DST_FOLDER%" 2>nul
del /q "%LOGFILE%" 2>nul
echo --- Build gestart op %DATE% %TIME% --- >> "%LOGFILE%"

rem ================================================
rem [3] pip + vereisten
rem ================================================
echo [3] 🔧 pip upgraden en requirements installeren...
"%PYEXE%" -m pip install --upgrade pip >nul
if exist requirements.txt (
  "%PYEXE%" -m pip install -r requirements.txt || (echo ❌ pip install -r faalde.& pause & exit /b 1)
)

rem ---- PyInstaller aanwezig? ----
"%PYEXE%" -c "import PyInstaller" >nul 2>&1 || (
  echo [3b] 📦 PyInstaller installeren...
  "%PYEXE%" -m pip install "pyinstaller>=6.0" "pyinstaller-hooks-contrib>=2025.0" || (
    echo ❌ Installatie PyInstaller faalde.& pause & exit /b 1
  )
)

rem ================================================
rem [4] PyInstaller build
rem ================================================
echo [4] 🛠 PyInstaller bouwen via %SPEC_FILE%...
"%PYEXE%" -m PyInstaller --clean --noconfirm "%SPEC_FILE%" >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo ❌ PyInstaller build faalde. Zie %LOGFILE%.& pause & exit /b 1)
if not exist "%INITIAL_EXE%" (
  echo ❌ EXE niet gevonden op "%INITIAL_EXE%". Zie %LOGFILE%.& pause & exit /b 1
)
echo ✅ Build geslaagd.

rem ================================================
rem [5] Map hernoemen naar versienummer
rem ================================================
echo [5] 🔁 Map hernoemen naar %BUILD_FOLDER%...
if exist "%DST_FOLDER%\%BUILD_FOLDER%" rmdir /S /Q "%DST_FOLDER%\%BUILD_FOLDER%"
rename "%DST_FOLDER%\%PROJECT_NAME%" "%BUILD_FOLDER%" >nul 2>&1
if errorlevel 1 (
  echo [rename] Fallback via robocopy...
  robocopy "%DST_FOLDER%\%PROJECT_NAME%" "%DST_FOLDER%\%BUILD_FOLDER%" /E /MOVE >nul
  if errorlevel 8 (echo ❌ Fallback kopie mislukt.& pause & exit /b 1)
  if exist "%DST_FOLDER%\%PROJECT_NAME%" rmdir /S /Q "%DST_FOLDER%\%PROJECT_NAME%"
)
if not exist "%DST_FOLDER%\%BUILD_FOLDER%\%PROJECT_NAME%.exe" (
  echo ❌ %PROJECT_NAME%.exe ontbreekt na hernoemen.& pause & exit /b 1
)

rem ================================================
rem [6] Extra bestanden kopiëren
rem ================================================
echo [6] 📁 Extra bestanden kopiëren...
for %%D in (assets css data config docs i18n models utils scripts md) do (
  if exist "%%D" xcopy /E /I /Y "%%D" "%DST_FOLDER%\%BUILD_FOLDER%\%%D" >nul
)
for %%F in (requirements.txt) do (
  if exist "%%F" copy /Y "%%F" "%DST_FOLDER%\%BUILD_FOLDER%\" >nul
)
> "%DST_FOLDER%\%BUILD_FOLDER%\version.txt" echo %NEW_VERSION%

rem ================================================
rem [7] Inno Setup installer bouwen
rem ================================================
set /p MAKE_INSTALLER=Ook Inno Setup installer bouwen? [J/N]: 
if /I "%MAKE_INSTALLER%"=="N" goto SHOW_OUTPUT

set "ISCC_EXE="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE (
  echo ⚠️  ISCC.exe niet gevonden. Installeer Inno Setup 6 of voeg het pad toe.
  goto SHOW_OUTPUT
)

echo [7] 🔨 Inno Setup compileren...
"%ISCC_EXE%" /DMyAppVersion=%NEW_VERSION% /DMySourceDir="..\dist\%BUILD_FOLDER%" "%ISS_FILE%"
if errorlevel 1 (
  echo ❌ Inno Setup compile mislukt. Controleer %ISS_FILE%.
  goto SHOW_OUTPUT
)
echo ✅ Installer aangemaakt: %DST_FOLDER%\%PROJECT_NAME%_setup_%NEW_VERSION%.exe

:SHOW_OUTPUT
echo.
echo ════════════════════════════════════════
echo  ✅ Build voltooid — versie %NEW_VERSION%
echo ════════════════════════════════════════
echo  📂 App-map:   %DST_FOLDER%\%BUILD_FOLDER%
echo  💡 Testen:    %DST_FOLDER%\%BUILD_FOLDER%\%PROJECT_NAME%.exe
echo  🧩 Installer: %DST_FOLDER%\%PROJECT_NAME%_setup_%NEW_VERSION%.exe
echo ════════════════════════════════════════
echo.
pause
endlocal