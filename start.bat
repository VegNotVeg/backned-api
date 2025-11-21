@echo off
chcp 65001 > nul
echo ======================================
echo  肾病AI分析系统 - 服务启动
echo ======================================
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 错误：虚拟环境激活失败，请先运行 setup_env.bat
    pause
    exit /b 1
)

echo 正在启动服务...
echo 服务地址：http://localhost:8000
echo API文档：http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo ======================================
python main.py

pause