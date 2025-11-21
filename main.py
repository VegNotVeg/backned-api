# 肾病AI分析系统后端 - Windows桌面版本
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
import logging
from pathlib import Path
import time
import uuid
import os
from enum import Enum

# 导入工具模块
import sys
sys.path.append('utils')
from wsi_processor import WSIProcessor
from model_manager import RenalAIModelManager

# ------------------------------
# 基础配置
# ------------------------------
app = FastAPI(
    title="肾病AI智能分析系统",
    description="支持病理报告生成、肾小球计数、细胞核计数三大功能",
    version="1.0.0"
)

# 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置 - 使用相对路径
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "data" / "results"
CONFIG_DIR = BASE_DIR / "config"
LOG_DIR = BASE_DIR / "logs"

# 创建必要目录
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 认证配置
SECRET_KEY = "renal_ai_desktop_secret_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "renal_ai.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------
# 数据模型定义
# ------------------------------
class AnalysisType(str, Enum):
    REPORT = "report"
    GLOMERULI_COUNT = "glomeruli_count"
    NUCLEI_COUNT = "nuclei_count"

class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class AnalysisRequest(BaseModel):
    analysis_type: AnalysisType
    file_id: str
    parameters: Optional[Dict[str, Any]] = None

# ------------------------------
# 模拟数据存储
# ------------------------------
fake_users_db = {}
uploaded_files = {}
analysis_tasks = {}

# ------------------------------
# 工具实例
# ------------------------------
wsi_processor = WSIProcessor()
model_manager = RenalAIModelManager(CONFIG_DIR / "models.yaml")

# ------------------------------
# 认证工具函数
# ------------------------------
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise HTTPException(status_code=401, detail="无效令牌")
        return fake_users_db[username]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌验证失败")

# ------------------------------
# API路由
# ------------------------------
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "status": "running",
        "service": "肾病AI分析系统桌面版",
        "timestamp": datetime.now().isoformat(),
        "data_path": str(BASE_DIR)
    }

@app.post("/api/register")
async def register(user: UserCreate):
    """用户注册"""
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    hashed_password = get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "created_at": datetime.now(timezone.utc)
    }
    fake_users_db[user.username] = user_data
    
    logger.info(f"新用户注册: {user.username}")
    return {"code": 200, "msg": "注册成功", "data": {"username": user.username}}

@app.post("/api/login")
async def login(login_data: LoginRequest):
    """用户登录"""
    user = fake_users_db.get(login_data.username)
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    access_token = create_access_token(
        data={"sub": login_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"用户登录: {login_data.username}")
    return {
        "code": 200,
        "msg": "登录成功",
        "data": {
            "token": access_token,
            "token_type": "bearer",
            "user_info": {
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"]
            }
        }
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    token: str = Depends(lambda x: x.headers.get("authorization", "").replace("Bearer ", ""))
):
    """上传病理图像文件"""
    try:
        current_user = await get_current_user(token)
    except:
        raise HTTPException(status_code=401, detail="请先登录")
    
    # 验证文件格式
    if not wsi_processor.is_wsi_file(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    
    # 生成文件ID
    file_id = f"{uuid.uuid4().hex}_{Path(file.filename).stem}"
    file_path = UPLOAD_DIR / f"{file_id}{Path(file.filename).suffix}"
    
    try:
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 获取文件信息
        metadata = wsi_processor.get_wsi_metadata(file_path)
        
        # 生成缩略图
        thumbnail_path = RESULTS_DIR / f"{file_id}_thumb.jpg"
        thumbnail_ok = wsi_processor.generate_thumbnail(file_path, thumbnail_path)
        
        # 保存文件记录
        uploaded_files[file_id] = {
            "original_name": file.filename,
            "saved_path": str(file_path),
            "file_size": len(content),
            "upload_time": datetime.now().isoformat(),
            "uploaded_by": current_user["username"],
            "metadata": metadata,
            "has_thumbnail": thumbnail_ok
        }
        
        logger.info(f"文件上传成功: {file.filename} -> {file_id}")
        
        return {
            "code": 200,
            "msg": "文件上传成功",
            "data": {
                "file_id": file_id,
                "original_name": file.filename,
                "file_size": len(content),
                "metadata": metadata,
                "thumbnail_available": thumbnail_ok
            }
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.post("/api/analyze")
async def analyze_image(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(lambda x: x.headers.get("authorization", "").replace("Bearer ", ""))
):
    """启动图像分析"""
    try:
        current_user = await get_current_user(token)
    except:
        raise HTTPException(status_code=401, detail="请先登录")
    
    # 验证文件存在
    if request.file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_info = uploaded_files[request.file_id]
    file_path = Path(file_info["saved_path"])
    
    # 生成任务ID
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # 创建任务记录
    analysis_tasks[task_id] = {
        "task_id": task_id,
        "analysis_type": request.analysis_type,
        "file_id": request.file_id,
        "status": "processing",
        "progress": 0,
        "start_time": datetime.now().isoformat(),
        "user": current_user["username"],
        "result": None,
        "error": None
    }
    
    # 启动后台任务
    if request.analysis_type == AnalysisType.REPORT:
        background_tasks.add_task(process_report, task_id, file_path, request.parameters or {})
    elif request.analysis_type == AnalysisType.GLOMERULI_COUNT:
        background_tasks.add_task(process_glomeruli, task_id, file_path, request.parameters or {})
    elif request.analysis_type == AnalysisType.NUCLEI_COUNT:
        background_tasks.add_task(process_nuclei, task_id, file_path, request.parameters or {})
    
    logger.info(f"分析任务启动: {task_id} - {request.analysis_type}")
    
    return {
        "code": 200,
        "msg": "分析任务已开始",
        "data": {
            "task_id": task_id,
            "analysis_type": request.analysis_type,
            "status": "processing"
        }
    }

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[task_id]
    return {
        "code": 200,
        "msg": "查询成功",
        "data": task
    }

@app.get("/api/files")
async def get_uploaded_files(token: str = Depends(lambda x: x.headers.get("authorization", "").replace("Bearer ", ""))):
    """获取已上传文件列表"""
    try:
        current_user = await get_current_user(token)
    except:
        raise HTTPException(status_code=401, detail="请先登录")
    
    user_files = {fid: info for fid, info in uploaded_files.items() if info["uploaded_by"] == current_user["username"]}
    
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "total_files": len(user_files),
            "files": user_files
        }
    }

# ------------------------------
# 后台任务处理函数
# ------------------------------
def process_report(task_id: str, file_path: Path, parameters: Dict):
    """处理报告生成任务"""
    try:
        task = analysis_tasks[task_id]
        task["progress"] = 30
        
        # 模拟处理时间
        time.sleep(2)
        
        # 调用模型生成报告
        result = model_manager.generate_pathology_report(file_path, parameters)
        
        task["progress"] = 100
        task["status"] = "completed"
        task["result"] = result
        task["complete_time"] = datetime.now().isoformat()
        
        logger.info(f"报告生成完成: {task_id}")
        
    except Exception as e:
        analysis_tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "complete_time": datetime.now().isoformat()
        })
        logger.error(f"报告生成失败: {e}")

def process_glomeruli(task_id: str, file_path: Path, parameters: Dict):
    """处理肾小球计数任务"""
    try:
        task = analysis_tasks[task_id]
        
        # 模拟分步处理
        for progress in [20, 40, 60, 80, 100]:
            time.sleep(0.6)
            task["progress"] = progress
        
        result = model_manager.count_glomeruli(file_path, parameters)
        
        task["status"] = "completed"
        task["result"] = result
        task["complete_time"] = datetime.now().isoformat()
        
        logger.info(f"肾小球计数完成: {task_id}")
        
    except Exception as e:
        analysis_tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "complete_time": datetime.now().isoformat()
        })
        logger.error(f"肾小球计数失败: {e}")

def process_nuclei(task_id: str, file_path: Path, parameters: Dict):
    """处理细胞核计数任务"""
    try:
        task = analysis_tasks[task_id]
        task["progress"] = 50
        time.sleep(1)
        
        result = model_manager.count_nuclei_in_glomerulus(file_path, parameters)
        
        task["progress"] = 100
        task["status"] = "completed"
        task["result"] = result
        task["complete_time"] = datetime.now().isoformat()
        
        logger.info(f"细胞核计数完成: {task_id}")
        
    except Exception as e:
        analysis_tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "complete_time": datetime.now().isoformat()
        })
        logger.error(f"细胞核计数失败: {e}")

# ------------------------------
# 启动服务
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("=== 肾病AI分析系统启动 ===")
    logger.info(f"服务地址: http://localhost:8000")
    logger.info(f"API文档: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )