@echo off
:: Register CEO Briefing in Windows Task Scheduler
:: Run this script ONCE as Administrator

set TASK_NAME=GoldTier_CEO_Briefing
set SCRIPT_PATH=D:\hack0aliza-gold\Scripts\run_ceo_briefing.bat

echo Registering Task Scheduler job: %TASK_NAME%

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "%SCRIPT_PATH%" ^
  /sc WEEKLY ^
  /d THU ^
  /st 12:00 ^
  /rl HIGHEST ^
  /f

if %ERRORLEVEL% == 0 (
    echo.
    echo SUCCESS — Task registered:
    echo   Name    : %TASK_NAME%
    echo   Runs    : Every Thursday at 12:00 PM
    echo   Script  : %SCRIPT_PATH%
    echo   Output  : D:\hack0aliza-gold\Briefings\
    echo.
    echo To verify: schtasks /query /tn "%TASK_NAME%"
    echo To run now: schtasks /run /tn "%TASK_NAME%"
    echo To remove: schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo FAILED — Run this script as Administrator
)
