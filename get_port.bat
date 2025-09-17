@echo off
REM 通用端口读取脚本
REM 使用方法: call get_port.bat
REM 结果存储在 %PORT% 变量中

set PORT=5000
if exist .env (
    for /f "tokens=2 delims==" %%a in ('findstr "APP_PORT" .env 2^>nul') do set PORT=%%a
)

