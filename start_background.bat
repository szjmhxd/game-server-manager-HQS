@echo off
cd /d "%~dp0"

REM -------------------------------
REM 读取端口配置
call get_port.bat

REM 检查 PORT 是否设置成功
if "%PORT%"=="" (
    echo 未获取到端口，请检查 get_port.bat
    pause
    exit /b
)

REM -------------------------------
REM 后台启动 Flask 应用并将日志写入 app.log
REM 使用 start 新窗口启动，避免阻塞当前批处理
start "" python -m flask run --host=0.0.0.0 --port=%PORT% --no-reload > app.log 2>&1

REM -------------------------------
REM 提示信息
echo ----------------------------------------
echo Flask应用已在后台启动
echo 日志文件: %~dp0app.log
echo 访问地址: http://localhost:%PORT%
echo 配置端口: %PORT%
echo ----------------------------------------
pause
