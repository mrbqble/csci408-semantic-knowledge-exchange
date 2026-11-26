Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
[void][Win32.Power]::SetThreadExecutionState([uint32](2147483648 + 1))
while (-not (Test-Path C:\Users\mrbqble\Desktop\csci408-probe\iter2\jobs\queue.done)) { Start-Sleep -Seconds 30 }
[void][Win32.Power]::SetThreadExecutionState([uint32]2147483648)
