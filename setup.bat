@echo off
:: ============================================================
:: Cracker's Toolkit — One-Click Setup Script
:: ============================================================
:: Run this script ONCE after extracting the release ZIP.
:: It downloads and sets up all external tools automatically.
:: Requires: Windows 10/11, internet connection.
:: ============================================================

setlocal enabledelayedexpansion
title Cracker's Toolkit Setup
color 0A

echo ============================================================
echo   Cracker's Toolkit - Dependency Setup
echo ============================================================
echo.

:: Determine script directory (where the exe lives)
set "BASE=%~dp0"
:: Remove trailing backslash
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

echo Install location: %BASE%
echo.

:: -------------------------------------------------------
:: 0. Ensure we can extract .7z archives
:: -------------------------------------------------------
set "SEVENZIP="
where 7z >nul 2>&1
if %errorlevel% equ 0 (
    set "SEVENZIP=7z"
) else (
    :: Check common install locations
    if exist "C:\Program Files\7-Zip\7z.exe" (
        set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"
    ) else if exist "C:\Program Files (x86)\7-Zip\7z.exe" (
        set "SEVENZIP=C:\Program Files (x86)\7-Zip\7z.exe"
    ) else (
        echo [0/5] 7-Zip not found — downloading standalone 7zr.exe...
        set "SEVENZIP=%TEMP%\7zr.exe"
        if not exist "!SEVENZIP!" (
            curl -L -o "!SEVENZIP!" "https://www.7-zip.org/a/7zr.exe" 2>nul
            if !errorlevel! neq 0 (
                echo       Failed to download 7zr.exe.
                set "SEVENZIP="
            ) else (
                echo       Downloaded 7zr.exe for .7z extraction.
            )
        ) else (
            echo       Using cached 7zr.exe.
        )
    )
)

:: -------------------------------------------------------
:: 1. Check / Install Python 3.12+
:: -------------------------------------------------------
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYVER=%%i"
    echo       Found Python !PYVER!
) else (
    echo       Python not found on PATH.
    echo.
    echo       Opening Python download page...
    echo       Please install Python 3.12+ and CHECK "Add to PATH".
    start https://www.python.org/downloads/
    echo.
    echo       After installing Python, re-run this setup script.
    pause
    exit /b 1
)

:: -------------------------------------------------------
:: 2. Download hashcat
:: -------------------------------------------------------
echo.
echo [2/5] Checking hashcat...
if exist "%BASE%\hashcat-7.1.2\hashcat.exe" (
    echo       Found hashcat at %BASE%\hashcat-7.1.2\hashcat.exe
) else (
    echo       Downloading hashcat 7.1.2...
    set "HC_URL=https://hashcat.net/files/hashcat-7.1.2.7z"
    set "HC_ZIP=%TEMP%\hashcat-7.1.2.7z"
    
    curl -L -o "!HC_ZIP!" "!HC_URL!" 2>nul
    if !errorlevel! neq 0 (
        echo       Download failed. Please download manually from:
        echo       https://hashcat.net/hashcat/
        echo       Extract to: %BASE%\hashcat-7.1.2\
    ) else (
        echo       Extracting hashcat...
        if defined SEVENZIP (
            "!SEVENZIP!" x "!HC_ZIP!" -o"%BASE%" -y >nul 2>&1
            if exist "%BASE%\hashcat-7.1.2\hashcat.exe" (
                echo       hashcat installed.
            ) else (
                echo       Extraction failed. Please download manually:
                echo       https://hashcat.net/hashcat/
                echo       Extract to: %BASE%\hashcat-7.1.2\
            )
        ) else (
            echo       Cannot extract .7z — 7-Zip not available.
            echo       Please download hashcat manually:
            echo       https://hashcat.net/hashcat/
            echo       Extract to: %BASE%\hashcat-7.1.2\
        )
    )
)

:: -------------------------------------------------------
:: 3. Download John the Ripper
:: -------------------------------------------------------
echo.
echo [3/5] Checking John the Ripper...
set "JTR_FOUND=0"
for /d %%d in ("%BASE%\john-*") do (
    if exist "%%d\run" set "JTR_FOUND=1"
)
if !JTR_FOUND! equ 1 (
    echo       Found John the Ripper.
) else (
    echo       Downloading John the Ripper 1.9.0 Jumbo 1...
    set "JTR_URL=https://www.openwall.com/john/k/john-1.9.0-jumbo-1-win64.zip"
    set "JTR_ZIP=%TEMP%\john-1.9.0-jumbo-1-win64.zip"
    
    curl -L -o "!JTR_ZIP!" "!JTR_URL!" 2>nul
    if !errorlevel! neq 0 (
        echo       Download failed. Please download manually from:
        echo       https://www.openwall.com/john/
        echo       Extract to: %BASE%\
    ) else (
        echo       Extracting John the Ripper...
        powershell -Command "Expand-Archive -Path '!JTR_ZIP!' -DestinationPath '%BASE%' -Force" 2>nul
        echo       John the Ripper installed.
    )
)

:: -------------------------------------------------------
:: 4. Download PRINCE Processor
:: -------------------------------------------------------
echo.
echo [4/5] Checking PRINCE Processor...
set "PP_FOUND=0"
if exist "%BASE%\Scripts_to_use\princeprocessor-master" set "PP_FOUND=1"
for %%f in ("%BASE%\pp64.exe" "%BASE%\pp.exe") do (
    if exist "%%f" set "PP_FOUND=1"
)
if !PP_FOUND! equ 1 (
    echo       Found PRINCE Processor.
) else (
    echo       Downloading PRINCE Processor...
    set "PP_URL=https://github.com/hashcat/princeprocessor/releases/download/v0.22/princeprocessor-0.22.7z"
    set "PP_ZIP=%TEMP%\princeprocessor.7z"
    
    curl -L -o "!PP_ZIP!" "!PP_URL!" 2>nul
    if !errorlevel! neq 0 (
        echo       Download failed. Please download manually from:
        echo       https://github.com/hashcat/princeprocessor/releases
    ) else (
        if defined SEVENZIP (
            if not exist "%BASE%\Scripts_to_use" mkdir "%BASE%\Scripts_to_use"
            "!SEVENZIP!" x "!PP_ZIP!" -o"%BASE%\Scripts_to_use\princeprocessor-master" -y >nul 2>&1
            echo       PRINCE Processor installed.
        ) else (
            echo       Cannot extract .7z — 7-Zip not available.
            echo       Please download manually from:
            echo       https://github.com/hashcat/princeprocessor/releases
        )
    )
)

:: -------------------------------------------------------
:: 5. Download PCFG Cracker + demeuk
:: -------------------------------------------------------
echo.
echo [5/5] Checking PCFG Cracker and demeuk...
set "PCFG_FOUND=0"
if exist "%BASE%\Scripts_to_use\pcfg_cracker-master" set "PCFG_FOUND=1"
if !PCFG_FOUND! equ 1 (
    echo       Found PCFG Cracker.
) else (
    echo       Downloading PCFG Cracker...
    set "PCFG_URL=https://github.com/lakiw/pcfg_cracker/archive/refs/heads/master.zip"
    set "PCFG_ZIP=%TEMP%\pcfg_cracker.zip"
    
    curl -L -o "!PCFG_ZIP!" "!PCFG_URL!" 2>nul
    if !errorlevel! neq 0 (
        echo       Download failed. Please download manually from:
        echo       https://github.com/lakiw/pcfg_cracker
    ) else (
        if not exist "%BASE%\Scripts_to_use" mkdir "%BASE%\Scripts_to_use"
        powershell -Command "Expand-Archive -Path '!PCFG_ZIP!' -DestinationPath '%BASE%\Scripts_to_use' -Force" 2>nul
        echo       PCFG Cracker installed.
    )
)

set "DEMEUK_FOUND=0"
if exist "%BASE%\Scripts_to_use\demeuk-master" set "DEMEUK_FOUND=1"
if !DEMEUK_FOUND! equ 1 (
    echo       Found demeuk.
) else (
    echo       Downloading demeuk...
    set "DM_URL=https://github.com/roeldev/demeuk/archive/refs/heads/master.zip"
    set "DM_ZIP=%TEMP%\demeuk.zip"
    
    curl -L -o "!DM_ZIP!" "!DM_URL!" 2>nul
    if !errorlevel! neq 0 (
        echo       Download failed. Please download manually from:
        echo       https://github.com/roeldev/demeuk
    ) else (
        if not exist "%BASE%\Scripts_to_use" mkdir "%BASE%\Scripts_to_use"
        powershell -Command "Expand-Archive -Path '!DM_ZIP!' -DestinationPath '%BASE%\Scripts_to_use' -Force" 2>nul
        echo       demeuk installed.
    )
)

:: -------------------------------------------------------
:: Summary
:: -------------------------------------------------------
echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo   You can now run CrackersToolkit.exe
echo.
echo   Optional (for Perl-based JtR extractors):
echo     Install Strawberry Perl: https://strawberryperl.com/
echo.
echo   The app will auto-detect tools on startup.
echo   Use Settings to manually configure paths if needed.
echo.
pause
