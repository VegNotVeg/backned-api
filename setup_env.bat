@echo off
chcp 65001 > nul  # 解决中文乱码
echo ======================================
echo  肾病AI分析系统 - 环境搭建（Python 3.13）
echo ======================================
echo 正在检查Python版本...
python --version | findstr "3.13" > nul
if errorlevel 1 (
    echo 错误：未检测到Python 3.13，请先安装并配置环境变量！
    pause
    exit /b 1
)

echo 正在创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo 错误：虚拟环境创建失败！
    pause
    exit /b 1
)

echo 正在激活虚拟环境并升级pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo 正在安装项目依赖（国内源加速）...
pip install --only-binary :all: -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo 警告：部分依赖安装失败，可手动执行 pip install -r requirements.txt
    echo 请确保已安装Visual C++ Build Tools 2022（如需编译）
) else (
    echo 环境搭建完成！
)
echo.
echo 下一步：双击运行 start.bat 启动服务
pause