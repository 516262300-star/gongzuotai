Option Explicit

Dim shell, fso, scriptDir, psScript, mode, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = fso.BuildPath(scriptDir, "workbench_autostart.ps1")
mode = "Ensure"

If WScript.Arguments.Count > 0 Then
    mode = WScript.Arguments.Item(0)
End If

command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & Quote(psScript) & " -Mode " & Quote(mode)
shell.Run command, 0, True

Function Quote(value)
    Quote = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
