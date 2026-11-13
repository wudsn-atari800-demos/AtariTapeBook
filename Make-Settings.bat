@echo off
rem Adds the folders of the build tools to the PATH.
rem This is the only file with machine-specific folders. Adapt it after installing the tools.
rem Python is expected to be in the PATH already.
set "MADS_DIR=C:\jac\system\Java\Programming\Repositories\wudsn-ide-tools\ASM\MADS\bin\windows_x86_64"
set "JAVA_DIR=C:\jac\system\Java\Tools\JDK\21\64-bit\jdk-21\bin"
set "TURGEN_DIR=C:\jac\system\Atari800\Tools\CAS\turgen-9.4.7"
set "ALTIRRA_BRIDGE_DIR=C:\jac\system\Atari800\Tools\EMU\AltirraSDL"
set "ALTIRRA_DIR=C:\jac\system\Atari800\Tools\EMU\Altirra"
set "PATH=%MADS_DIR%;%JAVA_DIR%;%TURGEN_DIR%;%ALTIRRA_BRIDGE_DIR%;%ALTIRRA_DIR%;%PATH%"
