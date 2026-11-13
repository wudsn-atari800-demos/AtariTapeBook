@echo off
rem Downloads the build tools into the "build" folder.
rem Tools that are already there are kept. Delete a tool's folder to download it again.
rem Python 3.9 or later must be installed globally.
setlocal
cd /d "%~dp0"
set "CURL=%SystemRoot%\System32\curl.exe"
set "TAR=%SystemRoot%\System32\tar.exe"

python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed. Install Python 3.9 or later from https://www.python.org/downloads/ and run this script again.
  exit /b 1
)

if not exist build mkdir build
call :install mads mads.exe https://raw.githubusercontent.com/wudsn/wudsn-ide-tools/main/ASM/MADS/bin/windows_x86_64/mads.exe exe || exit /b 1
call :install java bin\java.exe https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jre/hotspot/normal/eclipse zip || exit /b 1
call :install turgen dist\turgen.jar https://sourceforge.net/projects/turgen/files/latest/download tar.bz2 || exit /b 1
call :install altirra-bridge AltirraBridgeServer.exe https://github.com/ilmenit/AltirraSDL/releases/download/nightly-bridge/AltirraBridge-nightly-windows-x86_64.zip zip || exit /b 1
call :install altirra Altirra.exe https://www.virtualdub.org/downloads/Altirra-4.40.zip zip || exit /b 1
echo All build tools are installed in the "build" folder.
exit /b 0

rem :install <folder> <file that must exist afterwards> <url> <exe, zip or tar.bz2>
:install
if exist "build\%~1\%~2" (
  echo %~1 is already installed.
  exit /b 0
)
echo Downloading %~1...
if exist build\download rmdir /s /q build\download
mkdir build\download
if /i "%~4"=="exe" (
  "%CURL%" -fsSL -o "build\download\%~2" "%~3" || goto :failed
) else (
  "%CURL%" -fsSL -o "build\download.%~4" "%~3" || goto :failed
  "%TAR%" -xf "build\download.%~4" -C build\download || goto :failed
  del "build\download.%~4"
)
rem The archive contains the files either directly or in a single top folder.
if exist "build\download\%~2" (
  move build\download "build\%~1" >nul
) else (
  for /d %%D in (build\download\*) do if exist "%%D\%~2" move "%%D" "build\%~1" >nul
  rmdir /s /q build\download
)
if not exist "build\%~1\%~2" goto :failed
exit /b 0

:failed
echo Installing %~1 from %~3 failed.
if exist build\download rmdir /s /q build\download
if exist "build\download.%~4" del "build\download.%~4"
exit /b 1
