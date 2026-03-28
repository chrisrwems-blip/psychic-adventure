# Stop all servers
Write-Host "Stopping servers..." -ForegroundColor Yellow
Get-Process -Name "python", "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Done. All servers stopped." -ForegroundColor Green
