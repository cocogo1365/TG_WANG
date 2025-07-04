#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG營銷系統雲端API服務
提供激活碼驗證和狀態查詢接口
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
import hashlib
from datetime import datetime, timedelta
import logging
import asyncio
from collections import defaultdict
import time

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TG營銷系統API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應該限制具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API密鑰（生產環境應該從環境變量讀取）
API_KEY = os.getenv("API_KEY", "tg-marketing-api-key-2024")

# 速率限制
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 10  # 每分鐘最多請求次數
RATE_LIMIT_WINDOW = 60    # 時間窗口（秒）

# 數據模型
class ActivationRequest(BaseModel):
    activation_code: str
    device_id: str
    device_info: Optional[Dict] = None

class ActivationResponse(BaseModel):
    valid: bool
    message: str
    plan_type: Optional[str] = None
    days: Optional[int] = None
    expires_at: Optional[str] = None
    features: Optional[list] = None

class StatusResponse(BaseModel):
    activated: bool
    plan_type: Optional[str] = None
    remaining_days: Optional[int] = None
    expires_at: Optional[str] = None
    activation_date: Optional[str] = None

# 輔助函數
def check_rate_limit(client_ip: str) -> bool:
    """檢查速率限制"""
    current_time = time.time()
    requests = rate_limit_storage[client_ip]
    
    # 清理過期的請求記錄
    requests[:] = [req_time for req_time in requests 
                  if current_time - req_time < RATE_LIMIT_WINDOW]
    
    if len(requests) >= RATE_LIMIT_REQUESTS:
        return False
    
    requests.append(current_time)
    return True

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """驗證API密鑰"""
    return x_api_key == API_KEY

def get_database() -> Dict:
    """獲取數據庫內容"""
    try:
        db_path = os.getenv("DB_PATH", "bot_database.json")
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"讀取數據庫失敗: {e}")
        raise HTTPException(status_code=500, detail="數據庫訪問錯誤")

def save_database(data: Dict):
    """保存數據庫"""
    try:
        db_path = os.getenv("DB_PATH", "bot_database.json")
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存數據庫失敗: {e}")
        raise HTTPException(status_code=500, detail="數據庫保存錯誤")

# API端點
@app.get("/")
async def root():
    """API根路徑"""
    return {
        "service": "TG營銷系統API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "verify_activation": "/api/verify_activation",
            "check_status": "/api/check_status/{device_id}",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

@app.post("/api/verify_activation", response_model=ActivationResponse)
async def verify_activation(
    request: ActivationRequest,
    req: Request,
    x_api_key: Optional[str] = Header(None)
):
    """驗證激活碼"""
    # API密鑰驗證
    if not verify_api_key(x_api_key):
        logger.warning(f"無效的API密鑰: {x_api_key}")
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    # 速率限制
    client_ip = req.client.host
    if not check_rate_limit(client_ip):
        logger.warning(f"速率限制: {client_ip}")
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")
    
    try:
        # 記錄請求
        logger.info(f"驗證請求 - 激活碼: {request.activation_code[:8]}..., 設備: {request.device_id}")
        
        # 獲取數據庫
        db = get_database()
        
        code = request.activation_code.strip().upper()
        
        # 檢查激活碼是否存在
        if code not in db.get('activation_codes', {}):
            logger.warning(f"激活碼不存在: {code}")
            return ActivationResponse(
                valid=False,
                message="激活碼不存在"
            )
        
        code_data = db['activation_codes'][code]
        
        # 檢查是否已使用
        if code_data.get('used', False):
            used_at = code_data.get('used_at', '未知時間')
            used_device = code_data.get('used_by_device', '未知設備')
            
            # 如果是同一設備，允許重新激活
            if used_device == request.device_id:
                logger.info(f"同設備重新激活: {code}")
                return ActivationResponse(
                    valid=True,
                    message="激活成功（同設備重新激活）",
                    plan_type=code_data.get('plan_type'),
                    days=code_data.get('days'),
                    expires_at=code_data.get('expires_at'),
                    features=get_plan_features(code_data.get('plan_type'))
                )
            else:
                logger.warning(f"激活碼已被其他設備使用: {code}")
                return ActivationResponse(
                    valid=False,
                    message=f"激活碼已於 {used_at} 在其他設備上使用"
                )
        
        # 檢查是否過期
        expires_at = code_data.get('expires_at')
        if expires_at:
            expire_time = datetime.fromisoformat(expires_at)
            if datetime.now() > expire_time:
                logger.warning(f"激活碼已過期: {code}")
                return ActivationResponse(
                    valid=False,
                    message=f"激活碼已於 {expire_time.strftime('%Y-%m-%d %H:%M')} 過期"
                )
        
        # 標記為已使用
        code_data['used'] = True
        code_data['used_at'] = datetime.now().isoformat()
        code_data['used_by_device'] = request.device_id
        
        if request.device_info:
            code_data['device_info'] = request.device_info
        
        # 更新統計
        if 'activation_count' in db.get('statistics', {}):
            db['statistics']['activation_count'] = db['statistics'].get('activation_count', 0) + 1
        
        # 保存數據庫
        save_database(db)
        
        logger.info(f"激活成功: {code} - {code_data.get('plan_type')}")
        
        return ActivationResponse(
            valid=True,
            message="激活成功",
            plan_type=code_data.get('plan_type'),
            days=code_data.get('days'),
            expires_at=expires_at,
            features=get_plan_features(code_data.get('plan_type'))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"驗證激活碼時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服務器內部錯誤")

@app.get("/api/check_status/{device_id}", response_model=StatusResponse)
async def check_status(
    device_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """檢查設備激活狀態"""
    # API密鑰驗證
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        logger.info(f"狀態查詢 - 設備: {device_id}")
        
        # 獲取數據庫
        db = get_database()
        
        # 查找該設備使用的激活碼
        for code, data in db.get('activation_codes', {}).items():
            if data.get('used_by_device') == device_id:
                expires_at = data.get('expires_at')
                if expires_at:
                    expire_time = datetime.fromisoformat(expires_at)
                    if datetime.now() < expire_time:
                        remaining_days = (expire_time - datetime.now()).days + 1
                        
                        return StatusResponse(
                            activated=True,
                            plan_type=data.get('plan_type'),
                            remaining_days=remaining_days,
                            expires_at=expires_at,
                            activation_date=data.get('used_at')
                        )
        
        logger.info(f"設備未激活: {device_id}")
        return StatusResponse(activated=False)
        
    except Exception as e:
        logger.error(f"檢查狀態時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服務器內部錯誤")

@app.get("/api/statistics")
async def get_statistics(
    x_api_key: Optional[str] = Header(None)
):
    """獲取統計信息（管理員專用）"""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        db = get_database()
        stats = db.get('statistics', {})
        
        # 計算額外統計
        activation_codes = db.get('activation_codes', {})
        total_codes = len(activation_codes)
        used_codes = sum(1 for code in activation_codes.values() if code.get('used'))
        
        # 按方案類型統計
        plan_stats = defaultdict(lambda: {'total': 0, 'used': 0})
        for code_data in activation_codes.values():
            plan_type = code_data.get('plan_type', 'unknown')
            plan_stats[plan_type]['total'] += 1
            if code_data.get('used'):
                plan_stats[plan_type]['used'] += 1
        
        return {
            "total_revenue": stats.get('total_revenue', 0),
            "total_codes": total_codes,
            "used_codes": used_codes,
            "activation_rate": f"{(used_codes/total_codes*100):.1f}%" if total_codes > 0 else "0%",
            "plan_statistics": dict(plan_stats),
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取統計信息時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服務器內部錯誤")

def get_plan_features(plan_type: str) -> list:
    """獲取方案功能列表"""
    features_map = {
        'trial': ['基礎功能', '限制100個操作/天', '2天體驗'],
        'weekly': ['完整功能', '無限制操作', '基礎客服', '7天使用'],
        'monthly': ['完整功能', '無限制操作', '優先客服', '數據導出', '30天使用'],
        'quarterly': ['完整功能', '無限制操作', 'VIP客服', '數據導出', 'API訪問', '90天使用'],
        'yearly': ['完整功能', '無限制操作', 'VIP客服', '數據導出', 'API訪問', '免費更新', '365天使用'],
        'lifetime': ['所有當前和未來功能', '最高優先級支持', '源碼授權', '永久使用']
    }
    
    return features_map.get(plan_type, ['標準功能'])

# 啟動事件
@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info("TG營銷系統API服務已啟動")
    logger.info(f"API密鑰已配置: {'是' if API_KEY else '否'}")
    
    # 檢查數據庫
    try:
        db = get_database()
        logger.info(f"數據庫連接成功，激活碼數量: {len(db.get('activation_codes', {}))}")
    except Exception as e:
        logger.error(f"數據庫連接失敗: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("TG營銷系統API服務已關閉")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)