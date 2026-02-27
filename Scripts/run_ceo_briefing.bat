@echo off
:: CEO Weekly Briefing — Task Scheduler launcher
:: Scheduled: Every Thursday at 12:00 PM
:: To register: run Scripts\schedule_briefing.bat as Administrator

set WORKSPACE=D:\hack0aliza-gold
set PYTHON=%WORKSPACE%\python\python.exe

:: Fallback to system Python if local not found
if not exist "%PYTHON%" set PYTHON=python

cd /d "%WORKSPACE%"
"%PYTHON%" Scripts\ceo_briefing.py >> Logs\task_scheduler.log 2>&1
