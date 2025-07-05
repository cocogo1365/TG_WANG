#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG激活碼API服務 - Railway部署版
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import json
import os
from datetime import datetime
import logging
import hashlib
import platform

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TG激活碼驗證API",
    description="TG營銷軟件激活碼驗證服務",
    version="1.0.0"
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
UPLOAD_DATA_DIR = os.getenv("UPLOAD_DATA_DIR", "uploaded_data")

# TG機器人配置（如果同時需要運行機器人）
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS")
TEST_MODE = os.getenv("TEST_MODE", "true")
USDT_ADDRESS = os.getenv("USDT_ADDRESS")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY")

# 數據模型
class ActivationRequest(BaseModel):
    activation_code: str
    device_id: str

class ActivationResponse(BaseModel):
    valid: bool
    message: str
    plan_type: Optional[str] = None
    days: Optional[int] = None
    expires_at: Optional[str] = None

class CollectedUserData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_premium: Optional[bool] = False
    bio: Optional[str] = None
    collected_at: str
    group_source: Optional[str] = None
    additional_data: Optional[Dict] = None

class CollectionInfo(BaseModel):
    collection_date: str
    collection_method: str
    target_groups: List[str]
    total_collected: int
    successful_collections: int
    collection_settings: Optional[Dict] = None

class DataUploadRequest(BaseModel):
    activation_code: str
    device_info: Dict
    collected_members: List[CollectedUserData]
    collection_info: CollectionInfo
    upload_timestamp: str

def get_database() -> Dict:
    """獲取數據庫"""
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"數據庫文件不存在: {DB_PATH}")
            # 返回基本結構
            return {
                "activation_codes": {},
                "orders": {},
                "users": {},
                "statistics": {}
            }
    except Exception as e:
        logger.error(f"讀取數據庫失敗: {e}")
        return {
            "activation_codes": {},
            "orders": {},
            "users": {},
            "statistics": {}
        }

def save_database(data: Dict):
    """保存數據庫"""
    try:
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("數據庫保存成功")
    except Exception as e:
        logger.error(f"保存數據庫失敗: {e}")

def verify_admin_api_key(x_admin_key: Optional[str] = Header(None)) -> bool:
    """驗證管理員API密鑰"""
    if x_admin_key != ADMIN_API_KEY:
        logger.warning(f"無效管理員API密鑰訪問: {x_admin_key}")
        raise HTTPException(status_code=401, detail="無效的管理員API密鑰")
    return True

def ensure_upload_directory():
    """確保上傳目錄存在"""
    if not os.path.exists(UPLOAD_DATA_DIR):
        os.makedirs(UPLOAD_DATA_DIR, exist_ok=True)
        logger.info(f"創建上傳目錄: {UPLOAD_DATA_DIR}")

def generate_device_fingerprint(device_info: Dict) -> str:
    """生成設備指紋"""
    fingerprint_data = f"{device_info.get('device_id', '')}-{device_info.get('mac_address', '')}-{device_info.get('cpu_id', '')}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]

@app.get("/")
async def root():
    """API根路徑"""
    return {
        "service": "TG激活碼驗證API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "verify": "/verify",
            "status": "/status/{device_id}",
            "health": "/health",
            "data_upload": "/api/data/upload",
            "admin_devices": "/admin/devices",
            "admin_device_data": "/admin/device/{device_id}/data"
        }
    }

@app.get("/health")
async def health():
    """健康檢查"""
    try:
        # 檢查數據庫
        db = get_database()
        codes_count = len(db.get('activation_codes', {}))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "activation_codes": codes_count
        }
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.post("/verify", response_model=ActivationResponse)
async def verify_activation(
    request: ActivationRequest,
    x_api_key: Optional[str] = Header(None)
):
    """驗證激活碼"""
    
    # 檢查API密鑰
    if x_api_key != API_KEY:
        logger.warning(f"無效API密鑰訪問: {x_api_key}")
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        code = request.activation_code.strip().upper()
        device_id = request.device_id
        
        logger.info(f"驗證激活碼: {code[:8]}... 設備: {device_id[:8]}...")
        
        # 檢查萬能密鑰
        if code == "SHOW1365":
            logger.info(f"✅ 萬能密鑰驗證成功: {code}")
            return ActivationResponse(
                valid=True,
                message="激活成功（萬能密鑰）",
                plan_type="旗艦版",
                days=99999,
                expires_at="2099-12-31T23:59:59"
            )
        
        # 獲取數據庫
        db = get_database()
        
        # 檢查激活碼是否存在
        activation_codes = db.get('activation_codes', {})
        if code not in activation_codes:
            logger.warning(f"激活碼不存在: {code}")
            return ActivationResponse(
                valid=False,
                message="激活碼不存在"
            )
        
        code_data = activation_codes[code]
        
        # 檢查是否已使用
        if code_data.get('used', False):
            used_device = code_data.get('used_by_device', '')
            
            # 如果是同一設備，允許重新激活
            if used_device == device_id:
                logger.info(f"同設備重新激活: {code}")
                return ActivationResponse(
                    valid=True,
                    message="激活成功（同設備重新激活）",
                    plan_type=code_data.get('plan_type'),
                    days=code_data.get('days'),
                    expires_at=code_data.get('expires_at')
                )
            else:
                logger.warning(f"激活碼已被其他設備使用: {code}")
                return ActivationResponse(
                    valid=False,
                    message="激活碼已被其他設備使用"
                )
        
        # 檢查是否過期
        expires_at = code_data.get('expires_at')
        if expires_at:
            try:
                expire_time = datetime.fromisoformat(expires_at)
                if datetime.now() > expire_time:
                    logger.warning(f"激活碼已過期: {code}")
                    return ActivationResponse(
                        valid=False,
                        message="激活碼已過期"
                    )
            except ValueError:
                logger.warning(f"無效的過期時間格式: {expires_at}")
        
        # 標記為已使用
        code_data['used'] = True
        code_data['used_at'] = datetime.now().isoformat()
        code_data['used_by_device'] = device_id
        
        # 保存數據庫
        save_database(db)
        
        logger.info(f"激活成功: {code} - {code_data.get('plan_type')}")
        
        return ActivationResponse(
            valid=True,
            message="激活成功",
            plan_type=code_data.get('plan_type'),
            days=code_data.get('days'),
            expires_at=expires_at
        )
        
    except Exception as e:
        logger.error(f"驗證過程出錯: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

@app.get("/status/{device_id}")
async def check_status(
    device_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """檢查設備激活狀態"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        logger.info(f"狀態查詢 - 設備: {device_id[:8]}...")
        
        # 檢查是否為萬能密鑰設備（可以通過某種標記識別）
        # 這裡簡單返回激活狀態，實際使用時萬能密鑰會在本地記住
        
        db = get_database()
        
        # 查找該設備的激活碼
        for code, data in db.get('activation_codes', {}).items():
            if data.get('used_by_device') == device_id:
                expires_at = data.get('expires_at')
                if expires_at:
                    try:
                        expire_time = datetime.fromisoformat(expires_at)
                        if datetime.now() < expire_time:
                            remaining_days = (expire_time - datetime.now()).days + 1
                            
                            return {
                                "activated": True,
                                "plan_type": data.get('plan_type'),
                                "remaining_days": remaining_days,
                                "expires_at": expires_at,
                                "activation_date": data.get('used_at')
                            }
                    except ValueError:
                        logger.warning(f"無效的過期時間格式: {expires_at}")
        
        logger.info(f"設備未激活: {device_id[:8]}...")
        return {"activated": False}
        
    except Exception as e:
        logger.error(f"狀態檢查出錯: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

@app.post("/sync/activation_code")
async def sync_activation_code(
    data: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """同步激活碼到數據庫"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        activation_code = data.get("activation_code")
        code_data = data.get("code_data")
        
        if not activation_code or not code_data:
            raise HTTPException(status_code=400, detail="缺少必要數據")
        
        logger.info(f"同步激活碼: {activation_code}")
        
        # 獲取數據庫
        db = get_database()
        
        # 添加激活碼
        db['activation_codes'][activation_code] = code_data
        
        # 更新統計
        if 'activations_generated' in db.get('statistics', {}):
            db['statistics']['activations_generated'] = db['statistics'].get('activations_generated', 0) + 1
        
        # 保存數據庫
        save_database(db)
        
        logger.info(f"✅ 激活碼 {activation_code} 已同步")
        
        return {"success": True, "message": "激活碼已同步"}
        
    except Exception as e:
        logger.error(f"同步激活碼失敗: {e}")
        raise HTTPException(status_code=500, detail="同步失敗")

@app.post("/sync/order")
async def sync_order(
    order_data: Dict,
    x_api_key: Optional[str] = Header(None)
):
    """同步訂單到數據庫"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        order_id = order_data.get("order_id")
        
        if not order_id:
            raise HTTPException(status_code=400, detail="缺少訂單ID")
        
        logger.info(f"同步訂單: {order_id}")
        
        # 獲取數據庫
        db = get_database()
        
        # 添加訂單
        db['orders'][order_id] = order_data
        
        # 更新統計
        if order_data.get('status') == 'paid':
            if 'total_revenue' in db.get('statistics', {}):
                db['statistics']['total_revenue'] = db['statistics'].get('total_revenue', 0) + order_data.get('amount', 0)
        
        # 保存數據庫
        save_database(db)
        
        logger.info(f"✅ 訂單 {order_id} 已同步")
        
        return {"success": True, "message": "訂單已同步"}
        
    except Exception as e:
        logger.error(f"同步訂單失敗: {e}")
        raise HTTPException(status_code=500, detail="同步失敗")

@app.get("/stats")
async def get_stats(x_api_key: Optional[str] = Header(None)):
    """獲取統計信息"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        db = get_database()
        activation_codes = db.get('activation_codes', {})
        
        total_codes = len(activation_codes)
        used_codes = sum(1 for code in activation_codes.values() if code.get('used'))
        
        # 按方案統計
        plan_stats = {}
        for code_data in activation_codes.values():
            plan_type = code_data.get('plan_type', 'unknown')
            if plan_type not in plan_stats:
                plan_stats[plan_type] = {'total': 0, 'used': 0}
            plan_stats[plan_type]['total'] += 1
            if code_data.get('used'):
                plan_stats[plan_type]['used'] += 1
        
        return {
            "total_codes": total_codes,
            "used_codes": used_codes,
            "usage_rate": f"{(used_codes/total_codes*100):.1f}%" if total_codes > 0 else "0%",
            "plan_statistics": plan_stats,
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取統計出錯: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

@app.post("/api/data/upload")
async def upload_collected_data(
    request: DataUploadRequest,
    x_api_key: Optional[str] = Header(None)
):
    """客戶數據上傳API"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        # 確保上傳目錄存在
        ensure_upload_directory()
        
        # 生成設備指紋和上傳ID
        device_fingerprint = generate_device_fingerprint(request.device_info)
        upload_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{device_fingerprint}"
        
        # 準備存儲數據
        upload_data = {
            "upload_id": upload_id,
            "activation_code": request.activation_code,
            "device_info": request.device_info,
            "device_fingerprint": device_fingerprint,
            "collected_members": [member.dict() for member in request.collected_members],
            "collection_info": request.collection_info.dict(),
            "upload_timestamp": request.upload_timestamp,
            "server_received_at": datetime.now().isoformat(),
            "total_members": len(request.collected_members)
        }
        
        # 保存到文件
        file_path = os.path.join(UPLOAD_DATA_DIR, f"{upload_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(upload_data, f, ensure_ascii=False, indent=2)
        
        # 更新數據庫統計
        db = get_database()
        if 'uploaded_data_stats' not in db:
            db['uploaded_data_stats'] = {}
        
        db['uploaded_data_stats'][upload_id] = {
            "device_fingerprint": device_fingerprint,
            "activation_code": request.activation_code,
            "upload_time": datetime.now().isoformat(),
            "total_members": len(request.collected_members),
            "file_path": file_path
        }
        
        save_database(db)
        
        logger.info(f"✅ 數據上傳成功: {upload_id} ({len(request.collected_members)} 條記錄)")
        
        return {
            "success": True,
            "message": "數據上傳成功",
            "upload_id": upload_id,
            "total_records": len(request.collected_members),
            "device_fingerprint": device_fingerprint
        }
        
    except Exception as e:
        logger.error(f"數據上傳失敗: {e}")
        raise HTTPException(status_code=500, detail="數據上傳失敗")

@app.get("/admin/devices")
async def get_all_devices(x_admin_key: Optional[str] = Header(None)):
    """獲取所有設備列表（管理員）"""
    
    verify_admin_api_key(x_admin_key)
    
    try:
        db = get_database()
        uploaded_stats = db.get('uploaded_data_stats', {})
        
        devices = {}
        for upload_id, stats in uploaded_stats.items():
            device_fp = stats['device_fingerprint']
            if device_fp not in devices:
                devices[device_fp] = {
                    "device_fingerprint": device_fp,
                    "activation_code": stats['activation_code'],
                    "total_uploads": 0,
                    "total_records": 0,
                    "last_upload": None,
                    "uploads": []
                }
            
            devices[device_fp]['total_uploads'] += 1
            devices[device_fp]['total_records'] += stats['total_members']
            
            if not devices[device_fp]['last_upload'] or stats['upload_time'] > devices[device_fp]['last_upload']:
                devices[device_fp]['last_upload'] = stats['upload_time']
            
            devices[device_fp]['uploads'].append({
                "upload_id": upload_id,
                "upload_time": stats['upload_time'],
                "total_members": stats['total_members']
            })
        
        return {
            "total_devices": len(devices),
            "devices": list(devices.values())
        }
        
    except Exception as e:
        logger.error(f"獲取設備列表失敗: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

@app.get("/admin/device/{device_id}/data")
async def get_device_data(
    device_id: str,
    x_admin_key: Optional[str] = Header(None)
):
    """獲取特定設備的上傳數據（管理員）"""
    
    verify_admin_api_key(x_admin_key)
    
    try:
        db = get_database()
        uploaded_stats = db.get('uploaded_data_stats', {})
        
        device_uploads = []
        for upload_id, stats in uploaded_stats.items():
            if stats['device_fingerprint'] == device_id:
                # 讀取具體數據文件
                file_path = stats.get('file_path')
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            upload_data = json.load(f)
                        device_uploads.append(upload_data)
                    except Exception as e:
                        logger.warning(f"讀取數據文件失敗: {file_path} - {e}")
        
        if not device_uploads:
            raise HTTPException(status_code=404, detail="設備數據不存在")
        
        return {
            "device_fingerprint": device_id,
            "total_uploads": len(device_uploads),
            "uploads": device_uploads
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取設備數據失敗: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

# 啟動事件
@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info("🚀 TG激活碼API服務已啟動")
    logger.info(f"🔑 API密鑰已配置: {'是' if API_KEY else '否'}")
    logger.info(f"🔐 管理員API密鑰已配置: {'是' if ADMIN_API_KEY else '否'}")
    logger.info(f"📂 數據庫路徑: {DB_PATH}")
    logger.info(f"📁 上傳目錄: {UPLOAD_DATA_DIR}")
    
    # 確保上傳目錄存在
    ensure_upload_directory()
    
    # 檢查數據庫
    try:
        db = get_database()
        codes_count = len(db.get('activation_codes', {}))
        uploads_count = len(db.get('uploaded_data_stats', {}))
        logger.info(f"📊 數據庫連接成功，激活碼數量: {codes_count}，上傳記錄: {uploads_count}")
    except Exception as e:
        logger.error(f"❌ 數據庫連接失敗: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("👋 TG激活碼API服務已關閉")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)