@echo off
rem ---------------------------------------------------------------
rem  Double-click entry for flashing + verifying KeyOled_Full.
rem  This file is intentionally pure ASCII: cmd.exe decodes .bat as
rem  ANSI/GBK, so non-ASCII bytes here would corrupt the command
rem  structure. All Chinese output is produced by the .ps1 below.
rem ---------------------------------------------------------------
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0flash_keyoled.ps1"
