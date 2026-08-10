@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "LOCAL_OPENSPEC=%SCRIPT_DIR%node_modules\.bin\openspec.cmd"

if not exist "%LOCAL_OPENSPEC%" goto :missing_dependency

pushd "%SCRIPT_DIR%" >nul
if errorlevel 1 goto :repository_unavailable

if /I "%~1"=="archive" goto :archive

call "%LOCAL_OPENSPEC%" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

:archive
node "%SCRIPT_DIR%tools\openspec_archive_compat.mjs" preflight
if errorlevel 1 (
  popd
  exit /b 1
)

call "%LOCAL_OPENSPEC%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  popd
  exit /b %EXIT_CODE%
)

node "%SCRIPT_DIR%tools\openspec_archive_compat.mjs" postflight
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

:missing_dependency
echo OpenSpec executable was not found in repository-local dependencies. 1>&2
echo Install the pinned project dependencies with: npm ci 1>&2
exit /b 1

:repository_unavailable
echo Unable to enter the repository directory containing openspec.cmd. 1>&2
exit /b 1
