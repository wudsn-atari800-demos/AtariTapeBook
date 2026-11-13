@echo off
rem Adds the build tools in the "build" folder to the PATH. Make-Setup.bat downloads them.
rem Python is expected to be installed globally.
set "BUILD_DIR=%~dp0build"
if not exist "%BUILD_DIR%\altirra\Altirra.exe" (
  echo The build tools are missing. Run Make-Setup.bat first.
  exit /b 1
)
set "PATH=%BUILD_DIR%\mads;%BUILD_DIR%\java\bin;%BUILD_DIR%\turgen;%BUILD_DIR%\altirra-bridge;%BUILD_DIR%\altirra;%BUILD_DIR%\a8cas\bin;%PATH%"
