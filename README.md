\# 肾病AI分析系统后端（Windows桌面版）

基于FastAPI的肾病病理图像AI分析后端，支持用户注册/登录、文件上传、病理分析等功能。



\## 环境要求

\- Windows 10/11（64位）

\- Python 3.13（64位，已配置环境变量）

\- 网络畅通（用于安装依赖）



\## 快速开始

1\. 解压项目压缩包到任意目录（如`D:\\renal\_ai\_backend`）

2\. 双击运行 `setup\_env.bat`，自动搭建Python虚拟环境并安装依赖

3\. 依赖安装完成后，双击运行 `start.bat`，启动后端服务

4\. 打开浏览器访问以下地址：

&nbsp;  - 服务健康检查：http://localhost:8000

&nbsp;  - API文档（可测试接口）：http://localhost:8000/docs



\## 核心功能接口

1\. \*\*用户注册\*\*：/api/register（POST）

2\. \*\*用户登录\*\*：/api/login（POST）

3\. \*\*文件上传\*\*：/api/upload（POST，需登录令牌）

4\. \*\*图像分析\*\*：/api/analyze（POST，需登录令牌）

5\. \*\*任务状态查询\*\*：/api/task-status/{task\_id}（GET）

6\. \*\*上传文件列表\*\*：/api/files（GET，需登录令牌）



\## 目录说明

\- `data/uploads`：存储上传的病理图像文件

\- `data/results`：存储分析结果和缩略图

\- `logs`：存储系统运行日志

\- `config`：存储AI模型配置文件

\- `utils`：存储图像处理和模型管理工具类



\## 常见问题

1\. \*\*Python 3.13未检测到\*\*：确认Python已添加到系统环境变量，或重新安装Python 3.13

2\. \*\*依赖安装失败\*\*：安装Visual C++ Build Tools 2022（勾选“桌面开发与C++”），再重新运行`setup\_env.bat`

3\. \*\*端口8000被占用\*\*：修改`main.py`中`port=8000`为其他端口（如8001），重启服务

4\. \*\*接口返回401\*\*：需先调用/login接口获取令牌，在请求头中添加`Authorization: Bearer {令牌}`

