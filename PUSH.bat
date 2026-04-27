@echo off
cd /d "%~dp0"

git add -A
if errorlevel 1 (
    echo Failed to stage files.
    pause
    exit /b 1
)

set /p MSG="Commit message: "
if "%MSG%"=="" set MSG=Update files

git commit -m "%MSG%"
if errorlevel 1 (
    echo Nothing to commit.
    pause
    exit /b 0
)

git push
if errorlevel 1 (
    echo Push failed.
    pause
    exit /b 1
)

echo.
echo Pushed successfully.
pause
