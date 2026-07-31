@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "LOCAL_OPENSPEC=%SCRIPT_DIR%node_modules\.bin\openspec.cmd"

if not exist "%LOCAL_OPENSPEC%" goto :missing_dependency

pushd "%SCRIPT_DIR%" >nul
if errorlevel 1 goto :repository_unavailable

call "%LOCAL_OPENSPEC%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" if /I "%~1"=="archive" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%tools\normalize_openspec_spec_eof.ps1" -RepositoryRoot "%SCRIPT_DIR%."
    if errorlevel 1 (
        set "EXIT_CODE=%ERRORLEVEL%"
    )
)
popd
exit /b %EXIT_CODE%

:missing_dependency
echo OpenSpec executable was not found in repository-local dependencies. 1>&2
echo Install the pinned project dependencies with: npm ci 1>&2
exit /b 1

:repository_unavailable
echo Unable to enter the repository directory containing openspec.cmd. 1>&2
exit /b 1
