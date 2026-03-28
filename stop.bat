@echo off
echo Stopping servers...
taskkill /f /fi "WINDOWTITLE eq Backend Server*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Frontend Server*" >nul 2>&1
taskkill /f /im "uvicorn.exe" >nul 2>&1
taskkill /f /im "node.exe" >nul 2>&1
echo Done. All servers stopped.
pause
