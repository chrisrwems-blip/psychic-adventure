Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d """ & Replace(WScript.ScriptFullName, "ArcLight.vbs", "") & """ && python run.py", 0, False
