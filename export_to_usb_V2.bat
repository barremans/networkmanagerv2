REM ============================================================
REM export_to_usb.bat
REM 
REM Beschrijving: Export script naar USB
REM Applicatie: networkmanager V2
REM Versie: 1.0.1
REM Auteur: Barremans
REM Wijzigingen v1.0.1:
REM  - Robocopy retries beperkt (/R:2 /W:2) zodat export niet “vast hangt”
REM  - Optioneel: probleemfile qtuiotouchplugin.dll uitsluiten (standaard AAN)
REM ============================================================

@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

:: === Config: probleemfile uitsluiten? (1 = ja, 0 = nee) ===
set "EXCLUDE_QT_TOUCH_DLL=1"
set "QT_TOUCH_DLL=qtuiotouchplugin.dll"

:: === 0) Starttijd (ISO) + timestamp voor doelfolder ===
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "Get-Date -Format o"`) do set "START_ISO=%%a"
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "TIMESTAMP=%%a"

echo.
echo ================= Project Export =================
echo Start: %START_ISO%
echo.

:: === 1) Bron kiezen ===
:CHOOSE_SOURCE_MODE
echo Kies bron:
echo   [1] Huidige map  : "%cd%"
echo   [2] Map ingeven  (pad intypen)
set /p SRCHOICE=Maak een keuze (1/2) ^> 
if "%SRCHOICE%"=="1" (
    set "SOURCE_FOLDER=%cd%"
) else if "%SRCHOICE%"=="2" (
    set /p SOURCE_FOLDER=Geef het volledige pad van de bronmap ^> 
) else (
    echo Ongeldige keuze. Probeer opnieuw.
    echo.
    goto CHOOSE_SOURCE_MODE
)

if "%SOURCE_FOLDER%"=="" (
    echo [FOUT] Geen bronmap opgegeven.
    goto :ABORT
)
if not exist "%SOURCE_FOLDER%" (
    echo [FOUT] Bronmap bestaat niet: "%SOURCE_FOLDER%"
    goto :ABORT
)

:: Normaliseer mogelijk trailing backslash weg
if "%SOURCE_FOLDER:~-1%"=="\" set "SOURCE_FOLDER=%SOURCE_FOLDER:~0,-1%"

echo [OK] Bronmap: "%SOURCE_FOLDER%"

:: === 2) Venv pad bepalen (standaard .\venv onder bron) ===
set "VENV_PATH=%SOURCE_FOLDER%\venv"

:: === 3) USB-station vragen ===
:ASK_USB
set /p USB_DRIVE=Geef de stationsletter van de USB-stick (bv. E): 
if "%USB_DRIVE%"=="" (
    echo [FOUT] Geen stationsletter ingevoerd. Probeer opnieuw.
    goto ASK_USB
)
if not exist "%USB_DRIVE%:\" (
    echo [FOUT] Station %USB_DRIVE%: bestaat niet of is niet toegankelijk. Probeer opnieuw.
    goto ASK_USB
)

set "USB_FOLDER=%USB_DRIVE%:\export_networkmanager_%TIMESTAMP%"

echo.
echo [INFO] Doelmap: "%USB_FOLDER%"

:: === 4) Doelmap aanmaken ===
if not exist "%USB_FOLDER%" (
    echo [INFO] Doelmap wordt aangemaakt...
    mkdir "%USB_FOLDER%"
    if errorlevel 1 (
        echo [FOUT] Kon doelmap niet aanmaken: "%USB_FOLDER%"
        goto :ABORT
    )
) else (
    echo [INFO] Doelmap bestaat al. Bestanden kunnen worden overschreven.
)

:: === Bevestiging ===
echo.
choice /M "Wil je de export starten"
if errorlevel 2 (
  echo Actie geannuleerd.
  goto :ABORT
)

:: === 5) requirements.txt genereren (indien venv aanwezig) ===
echo.
echo [0] Pip freeze uitvoeren (vereist geactiveerde venv)...
set "REQ_FILE=%SOURCE_FOLDER%\requirements.txt"

if exist "%VENV_PATH%\Scripts\activate.bat" (
    call "%VENV_PATH%\Scripts\activate.bat"
    if errorlevel 1 (
        echo [WAARSCHUWING] Kon venv niet activeren: "%VENV_PATH%"
    )
    where pip >nul 2>&1
    if errorlevel 1 (
        echo [WAARSCHUWING] 'pip' niet gevonden na activeren venv. Sla requirements.txt over.
    ) else (
        pip freeze > "%REQ_FILE%" 2>nul
        if exist "%REQ_FILE%" (
            echo [OK] requirements.txt aangemaakt in bronmap.
        ) else (
            echo [FOUT] requirements.txt kon niet worden aangemaakt.
        )
    )
) else (
    echo [INFO] Geen virtuele omgeving gevonden in: "%VENV_PATH%"
    echo [INFO] requirements.txt wordt niet aangemaakt.
)

:: === 6) Project kopiëren (excl. map "zzz") ===
echo.
echo [1] Kopiëren van projectmap (excl. "zzz") met voortgang...

:: Robocopy retry gedrag beperken zodat export niet vastloopt:
set "ROBO_RETRY=/R:2 /W:2"

:: Optioneel probleemfile uitsluiten:
set "ROBO_EXCLUDE_FILE="
if "%EXCLUDE_QT_TOUCH_DLL%"=="1" (
    set "ROBO_EXCLUDE_FILE=/XF %QT_TOUCH_DLL%"
    echo [INFO] Uitsluiten bestand: %QT_TOUCH_DLL%
)

robocopy "%SOURCE_FOLDER%" "%USB_FOLDER%" /E /XD "%SOURCE_FOLDER%\zzz" %ROBO_RETRY% %ROBO_EXCLUDE_FILE% /ETA /FP
set "RC=%ERRORLEVEL%"

:: Robocopy exit-codes: 0/1/2/3/4/5/6/7 zijn OK/waarschuwingen; >=8 is fout
if %RC% GEQ 8 (
    echo [FOUT] Robocopy gaf foutcode %RC%.
    goto :ABORT
) else (
    echo [OK] Bestanden en submappen (zonder "zzz") gekopieerd. (RC=%RC%)
)

:: === 7) Virtuele omgeving meenemen (optioneel) ===
if exist "%VENV_PATH%" (
    echo.
    choice /M "Virtuele omgeving (venv) ook kopiëren"
    if errorlevel 2 (
        echo [INFO] Venv kopiëren overgeslagen.
    ) else (
        echo [2] Kopiëren van virtuele omgeving...
        robocopy "%VENV_PATH%" "%USB_FOLDER%\venv" /E %ROBO_RETRY% /ETA /FP
        set "RCV=%ERRORLEVEL%"
        if %RCV% GEQ 8 (
            echo [WAARSCHUWING] Fout bij kopiëren venv (RC=%RCV%).
        ) else (
            echo [OK] Virtuele omgeving gekopieerd. (RC=%RCV%)
        )
    )
) else (
    echo.
    echo [INFO] Geen virtuele omgeving gevonden op "%VENV_PATH%". Wordt niet meegenomen.
)

:: === 8) Logbestand schrijven ===
echo.
echo [3] Logbestand schrijven...
(
    echo Laatste export: %DATE% %TIME%
    echo Bronmap: %SOURCE_FOLDER%
    echo Bestemming: %USB_FOLDER%
    echo Virtuele omgeving-pad: %VENV_PATH%
    echo requirements.txt aanwezig:
    if exist "%REQ_FILE%" (echo   JA) else (echo   NEE)
    echo Map "zzz" uitgesloten
    echo Robocopy retry: %ROBO_RETRY%
    echo Exclude qtuiotouchplugin.dll: %EXCLUDE_QT_TOUCH_DLL%
) > "%USB_FOLDER%\export_log.txt"
echo [OK] Logbestand aangemaakt: "%USB_FOLDER%\export_log.txt"

:: === 9) Eindtijd en totale duur berekenen ===
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "Get-Date -Format o"`) do set "END_ISO=%%a"

for /f "usebackq tokens=*" %%a in (`
  powershell -NoProfile -Command ^
    "[int][math]::Round((New-TimeSpan -Start ([datetime]'%START_ISO%') -End ([datetime]'%END_ISO%')).TotalSeconds)"
`) do set "DURATION=%%a"

if not defined DURATION set "DURATION=0"
if !DURATION! LSS 0 set /a DURATION+=86400

set /a h=DURATION/3600
set /a m=(DURATION%%3600)/60
set /a s=DURATION%%60

echo.
echo ================= Resultaat =================
echo Starttijd (ISO): %START_ISO%
echo Eindtijd  (ISO): %END_ISO%
echo Totale duur    : !h! uur !m! min !s! sec
echo.
echo Export succesvol afgerond.
echo Project staat nu op: "%USB_FOLDER%"
echo ============================================================
echo.
pause
goto :EOF

:ABORT
echo.
echo ==== Afgebroken ====
pause
exit /b 1