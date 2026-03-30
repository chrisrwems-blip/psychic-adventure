@echo off
title ArcLight Installer
color 0B
echo.
echo  ============================================
echo    ArcLight Installer
echo    Data Center Electrical Submittal Review
echo  ============================================
echo.
echo  This will install ArcLight on your computer.
echo  It may take a few minutes on the first run.
echo.
pause

:: -------------------------------------------
:: Check for Python
:: -------------------------------------------
echo.
echo  [1/5] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python not found. Downloading installer...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo  Running Python installer — CHECK "Add Python to PATH" then click Install Now
    start /wait %TEMP%\python_installer.exe InstallAllUsers=0 PrependPath=1 Include_pip=1
    del %TEMP%\python_installer.exe
    :: Refresh PATH
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\;%LOCALAPPDATA%\Programs\Python\Python312\Scripts\;%PATH%"
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Python installation failed.
        echo  Please install Python manually from https://www.python.org/downloads/
        echo  IMPORTANT: Check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
    echo  Python installed successfully.
) else (
    for /f "tokens=*" %%v in ('python --version') do echo  Found %%v
)

:: -------------------------------------------
:: Check for Node.js
:: -------------------------------------------
echo.
echo  [2/5] Checking for Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Node.js not found. Downloading installer...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi' -OutFile '%TEMP%\node_installer.msi'"
    echo  Running Node.js installer — click Next through all screens.
    start /wait msiexec /i %TEMP%\node_installer.msi /qn
    del %TEMP%\node_installer.msi
    :: Refresh PATH
    set "PATH=C:\Program Files\nodejs\;%PATH%"
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Node.js installation failed.
        echo  Please install Node.js manually from https://nodejs.org/
        pause
        exit /b 1
    )
    echo  Node.js installed successfully.
) else (
    for /f "tokens=*" %%v in ('node --version') do echo  Found Node.js %%v
)

:: -------------------------------------------
:: Check for Git
:: -------------------------------------------
echo.
echo  [3/5] Checking for Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Git not found. Downloading installer...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'"
    echo  Running Git installer — click Next through all screens.
    start /wait %TEMP%\git_installer.exe /VERYSILENT /NORESTART
    del %TEMP%\git_installer.exe
    :: Refresh PATH
    set "PATH=C:\Program Files\Git\cmd\;%PATH%"
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Git installation failed.
        echo  Please install Git manually from https://git-scm.com/download/win
        pause
        exit /b 1
    )
    echo  Git installed successfully.
) else (
    for /f "tokens=*" %%v in ('git --version') do echo  Found %%v
)

:: -------------------------------------------
:: Download ArcLight
:: -------------------------------------------
echo.
echo  [4/5] Downloading ArcLight...
set "INSTALL_DIR=%USERPROFILE%\ArcLight"

if exist "%INSTALL_DIR%\.git" (
    echo  ArcLight already downloaded. Updating...
    cd /d "%INSTALL_DIR%"
    git pull origin main
) else (
    if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
    git clone https://github.com/chrisrwems-blip/psychic-adventure.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)

:: -------------------------------------------
:: Build the .exe
:: -------------------------------------------
echo.
echo  [5/5] Building ArcLight.exe — this may take a few minutes...
echo.
pip install pyinstaller >nul 2>&1
cd /d "%INSTALL_DIR%"
python build_exe.py

if not exist "%INSTALL_DIR%\dist\ArcLight.exe" (
    echo.
    echo  ERROR: Build failed. Check the output above for errors.
    pause
    exit /b 1
)

:: -------------------------------------------
:: Create Desktop Shortcut
:: -------------------------------------------
echo.
echo  Creating desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'ArcLight.lnk')); $s.TargetPath = '%INSTALL_DIR%\dist\ArcLight.exe'; $s.WorkingDirectory = '%INSTALL_DIR%\dist'; $s.Description = 'ArcLight - Data Center Submittal Review'; $s.Save()"

:: -------------------------------------------
:: Done
:: -------------------------------------------
echo.
echo  ============================================
echo    Installation Complete!
echo  ============================================
echo.
echo  ArcLight.exe is at:
echo    %INSTALL_DIR%\dist\ArcLight.exe
echo.
echo  A shortcut has been created on your Desktop.
echo  Double-click "ArcLight" to start.
echo.
pause

:: Launch it
start "" "%INSTALL_DIR%\dist\ArcLight.exe"
