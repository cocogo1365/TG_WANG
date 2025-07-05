#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG激活碼API服務 + 數據管理API - Railway部署版
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import json
import os
import hashlib
from datetime import datetime
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TG營銷系統API",
    description="TG營銷軟件激活碼驗證和數據管理服務",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 從環境變量獲取配置
API_KEY = os.getenv("API_KEY", "tg-api-secure-key-2024")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secure-key-2024")
DB_PATH = os.getenv("DB_PATH", "bot_database.json")

# 數據存儲路徑
DATA_STORAGE_PATH = "uploaded_data"
os.makedirs(DATA_STORAGE_PATH, exist_ok=True)

# TG機器人配置（如果同時需要運行機器人）
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS")
TEST_MODE = os.getenv("TEST_MODE", "true")
USDT_ADDRESS = os.getenv("USDT_ADDRESS")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY")

# ===================================================================
# 激活碼相關數據模型
# ===================================================================

class ActivationRequest(BaseModel):
    activation_code: str
    device_id: str

class ActivationResponse(BaseModel):
    valid: bool
    message: str
    plan_type: Optional[str] = None
    days: Optional[int] = None
    expires_at: Optional[str] = None

# ===================================================================
# 數據收集相關數據模型
# ===================================================================

class CollectedUserData(BaseModel):
    user_id: str
    username: Optional[str] = ""
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    phone: Optional[str] = ""
    is_bot: bool = False
    is_verified: bool = False
    is_premium: bool = False
    user_status: Optional[str] = ""
    group_role: str = "member"
    group_name: str
    group_id: Optional[str] = ""
    collection_timestamp: str
    data_hash: Optional[str] = ""

class CollectionInfo(BaseModel):
    timestamp: str
    group_name: str
    group_id: Optional[str] = ""
    collection_type: str = "members"
    total_count: int
    software_version: str = "TG旺專業版"

class BatchInfo(BaseModel):
    batch_number: int
    total_batches: int
    batch_size: int

class DataUploadRequest(BaseModel):
    device_id: str
    activation_code: str
    collection_info: CollectionInfo
    collected_data: List[CollectedUserData]
    batch_info: Optional[BatchInfo] = None

# ===================================================================
# 工具函數
# ===================================================================

def load_database():
    """載入激活碼數據庫"""
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"載入數據庫失敗: {e}")
    
    # 返回默認數據庫結構
    return {
        "activation_codes": {
            "2WQ67T9TAVMS9MWR": {
                "activation_code": "2WQ67T9TAVMS9MWR",
                "plan_type": "trial",
                "days": 2,
                "created_at": "2025-01-04T10:00:00",
                "expires_at": "2025-01-06T10:00:00",
                "used": False,
                "used_at": None,
                "used_by_device": None
            }
        },
        "users": {},
        "orders": {}
    }

def verify_api_key(x_api_key: str = Header(...)):
    """驗證API密鑰"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

def verify_admin_key(x_admin_key: str = Header(...)):
    """驗證管理員API密鑰"""
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return x_admin_key

# ===================================================================
# 基礎API端點
# ===================================================================

@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "TG營銷系統API",
        "version": "2.0.0",
        "features": ["激活碼驗證", "數據收集", "管理後台"],
        "status": "運行中",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康檢查"""
    database = load_database()
    activation_count = len(database.get("activation_codes", {}))
    
    return {
        "status": "healthy",
        "service": "TG營銷系統API",
        "activation_codes": activation_count,
        "timestamp": datetime.now().isoformat()
    }

# ===================================================================
# 激活碼驗證API
# ===================================================================

@app.post("/verify", response_model=ActivationResponse)
async def verify_activation_code(request: ActivationRequest):
    """驗證激活碼"""
    try:
        activation_code = request.activation_code.strip().upper()
        device_id = request.device_id
        
        if not activation_code:
            return ActivationResponse(valid=False, message="激活碼不能為空")
        
        database = load_database()
        activation_codes = database.get("activation_codes", {})
        
        # 檢查激活碼是否存在
        if activation_code not in activation_codes:
            return ActivationResponse(valid=False, message="激活碼不存在")
        
        code_data = activation_codes[activation_code]
        
        # 檢查是否已使用
        if code_data.get("used", False):
            used_at = code_data.get("used_at", "未知時間")
            return ActivationResponse(valid=False, message=f"激活碼已於 {used_at} 使用過")
        
        # 檢查是否過期
        expires_at_str = code_data.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    return ActivationResponse(
                        valid=False, 
                        message=f"激活碼已於 {expires_at.strftime('%Y-%m-%d %H:%M:%S')} 過期"
                    )
            except:
                pass
        
        # 激活碼有效
        return ActivationResponse(
            valid=True,
            message="激活碼驗證成功",
            plan_type=code_data.get("plan_type"),
            days=code_data.get("days"),
            expires_at=code_data.get("expires_at")
        )
        
    except Exception as e:
        logger.error(f"驗證激活碼時發生錯誤: {e}")
        return ActivationResponse(valid=False, message=f"驗證過程發生錯誤: {str(e)}")

# ===================================================================
# 數據收集API
# ===================================================================

@app.post("/api/data/upload")
async def upload_collected_data(
    request: DataUploadRequest,
    api_key: str = Depends(verify_api_key)
):
    """上傳採集數據"""
    try:
        # 驗證激活碼
        database = load_database()
        activation_codes = database.get("activation_codes", {})
        
        if request.activation_code not in activation_codes:
            raise HTTPException(status_code=403, detail="Invalid activation code")
        
        # 生成上傳ID
        upload_id = hashlib.md5(f"{request.device_id}-{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # 存儲數據
        device_dir = os.path.join(DATA_STORAGE_PATH, request.device_id)
        os.makedirs(device_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = os.path.join(device_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        
        # 保存數據文件
        data_file = os.path.join(date_dir, f"{upload_id}_data.json")
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump([item.dict() for item in request.collected_data], f, ensure_ascii=False, indent=2)
        
        # 保存上傳記錄
        upload_record = {
            "upload_id": upload_id,
            "device_id": request.device_id,
            "activation_code": request.activation_code,
            "collection_info": request.collection_info.dict(),
            "batch_info": request.batch_info.dict() if request.batch_info else None,
            "upload_timestamp": datetime.now().isoformat(),
            "data_count": len(request.collected_data),
            "processed": True
        }
        
        record_file = os.path.join(date_dir, f"{upload_id}_record.json")
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(upload_record, f, ensure_ascii=False, indent=2)
        
        # 更新設備索引
        index_file = os.path.join(device_dir, "upload_index.json")
        upload_index = []
        
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    upload_index = json.load(f)
            except:
                upload_index = []
        
        upload_index.append({
            "upload_id": upload_id,
            "timestamp": upload_record["upload_timestamp"],
            "group_name": request.collection_info.group_name,
            "collection_type": request.collection_info.collection_type,
            "data_count": len(request.collected_data),
            "batch_info": request.batch_info.dict() if request.batch_info else None
        })
        
        # 只保留最近100條記錄
        if len(upload_index) > 100:
            upload_index = upload_index[-100:]
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(upload_index, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Data uploaded successfully: {upload_id} from device {request.device_id}")
        
        return {
            "success": True,
            "message": f"數據上傳成功，處理了 {len(request.collected_data)} 條記錄",
            "upload_id": upload_id,
            "processed_count": len(request.collected_data)
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/auth/upload")
async def authenticate_upload(
    request: dict,
    api_key: str = Depends(verify_api_key)
):
    """驗證上傳授權"""
    try:
        device_id = request.get("device_id")
        activation_code = request.get("activation_code")
        
        if not device_id or not activation_code:
            raise HTTPException(status_code=400, detail="Missing device_id or activation_code")
        
        database = load_database()
        activation_codes = database.get("activation_codes", {})
        
        if activation_code in activation_codes:
            return {
                "success": True,
                "message": "Upload authorization granted",
                "device_id": device_id,
                "authorized_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=403, detail="Authorization failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Auth failed: {str(e)}")

@app.get("/api/data/download/{device_id}/{upload_id}")
async def download_upload_data(
    device_id: str,
    upload_id: str,
    api_key: str = Depends(verify_api_key)
):
    """下載特定上傳的數據"""
    try:
        device_dir = os.path.join(DATA_STORAGE_PATH, device_id)
        
        if not os.path.exists(device_dir):
            raise HTTPException(status_code=404, detail="Device not found")
        
        # 搜索所有日期目錄
        data_file = None
        for item in os.listdir(device_dir):
            date_path = os.path.join(device_dir, item)
            if os.path.isdir(date_path):
                potential_file = os.path.join(date_path, f"{upload_id}_data.json")
                if os.path.exists(potential_file):
                    data_file = potential_file
                    break
        
        if not data_file:
            raise HTTPException(status_code=404, detail="Data file not found")
        
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            "success": True,
            "upload_id": upload_id,
            "device_id": device_id,
            "data": data,
            "count": len(data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# ===================================================================
# 管理後台API
# ===================================================================

@app.get("/admin/devices")
async def list_devices(admin_key: str = Depends(verify_admin_key)):
    """獲取所有設備列表"""
    try:
        devices = []
        
        if not os.path.exists(DATA_STORAGE_PATH):
            return {"devices": devices, "total": 0, "total_records": 0}
        
        total_records = 0
        
        for device_id in os.listdir(DATA_STORAGE_PATH):
            device_dir = os.path.join(DATA_STORAGE_PATH, device_id)
            if not os.path.isdir(device_dir):
                continue
            
            index_file = os.path.join(device_dir, "upload_index.json")
            device_info = {
                "device_id": device_id,
                "total_uploads": 0,
                "total_records": 0,
                "last_upload": None,
                "groups": []
            }
            
            if os.path.exists(index_file):
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        upload_index = json.load(f)
                    
                    device_info["total_uploads"] = len(upload_index)
                    device_info["total_records"] = sum(u.get("data_count", 0) for u in upload_index)
                    total_records += device_info["total_records"]
                    
                    if upload_index:
                        device_info["last_upload"] = upload_index[-1].get("timestamp")
                        device_info["groups"] = list(set(u.get("group_name", "") for u in upload_index if u.get("group_name")))
                    
                except Exception as e:
                    logger.error(f"Error reading device {device_id} index: {e}")
            
            devices.append(device_info)
        
        # 按最後上傳時間排序
        devices.sort(key=lambda x: x.get("last_upload", ""), reverse=True)
        
        return {
            "devices": devices,
            "total": len(devices),
            "total_records": total_records
        }
        
    except Exception as e:
        logger.error(f"List devices failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")

@app.get("/admin/device/{device_id}/data")
async def get_device_data(
    device_id: str,
    page: int = 1,
    per_page: int = 20,
    admin_key: str = Depends(verify_admin_key)
):
    """獲取特定設備的數據"""
    try:
        device_dir = os.path.join(DATA_STORAGE_PATH, device_id)
        index_file = os.path.join(device_dir, "upload_index.json")
        
        if not os.path.exists(index_file):
            return {
                "device_id": device_id,
                "uploads": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "has_next": False
            }
        
        with open(index_file, "r", encoding="utf-8") as f:
            upload_index = json.load(f)
        
        # 按時間倒序排列
        upload_index.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 分頁
        total = len(upload_index)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_uploads = upload_index[start_idx:end_idx]
        
        return {
            "device_id": device_id,
            "uploads": page_uploads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": end_idx < total
        }
        
    except Exception as e:
        logger.error(f"Get device data failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get device data: {str(e)}")

# ===================================================================
# 啟動配置
# ===================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)