#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版雲端API - 專門用於激活碼驗證
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
from datetime import datetime
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TG激活碼API", version="1.0.0")

# API密鑰（從環境變量獲取）
API_KEY = os.getenv("API_KEY", "tg-api-2024")

class ActivationRequest(BaseModel):
    activation_code: str
    device_id: str

class ActivationResponse(BaseModel):
    valid: bool
    message: str
    plan_type: Optional[str] = None
    days: Optional[int] = None
    expires_at: Optional[str] = None

def get_database() -> Dict:
    """獲取數據庫"""
    try:
        db_path = os.getenv("DB_PATH", "bot_database.json")
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"讀取數據庫失敗: {e}")
        # 返回空數據庫結構
        return {
            "activation_codes": {},
            "orders": {},
            "users": {},
            "statistics": {}
        }

def save_database(data: Dict):
    """保存數據庫"""
    try:
        db_path = os.getenv("DB_PATH", "bot_database.json")
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存數據庫失敗: {e}")

@app.get("/")
async def root():
    """API根路徑"""
    return {
        "service": "TG激活碼驗證API",
        "version": "1.0.0", 
        "status": "online"
    }

@app.get("/health")
async def health():
    """健康檢查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/verify", response_model=ActivationResponse)
async def verify_activation(
    request: ActivationRequest,
    x_api_key: Optional[str] = Header(None)
):
    """驗證激活碼"""
    
    # 檢查API密鑰
    if x_api_key != API_KEY:
        logger.warning(f"無效API密鑰: {x_api_key}")
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        code = request.activation_code.strip().upper()
        device_id = request.device_id
        
        logger.info(f"驗證激活碼: {code[:8]}... 設備: {device_id}")
        
        # 獲取數據庫
        db = get_database()
        
        # 檢查激活碼是否存在
        if code not in db.get('activation_codes', {}):
            return ActivationResponse(
                valid=False,
                message="激活碼不存在"
            )
        
        code_data = db['activation_codes'][code]
        
        # 檢查是否已使用
        if code_data.get('used', False):
            used_device = code_data.get('used_by_device', '')
            
            # 如果是同一設備，允許重新激活
            if used_device == device_id:
                return ActivationResponse(
                    valid=True,
                    message="激活成功（同設備）",
                    plan_type=code_data.get('plan_type'),
                    days=code_data.get('days'),
                    expires_at=code_data.get('expires_at')
                )
            else:
                return ActivationResponse(
                    valid=False,
                    message="激活碼已被其他設備使用"
                )
        
        # 檢查是否過期
        expires_at = code_data.get('expires_at')
        if expires_at:
            expire_time = datetime.fromisoformat(expires_at)
            if datetime.now() > expire_time:
                return ActivationResponse(
                    valid=False,
                    message="激活碼已過期"
                )
        
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
async def check_status(device_id: str, x_api_key: Optional[str] = Header(None)):
    """檢查設備激活狀態"""
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="無效的API密鑰")
    
    try:
        db = get_database()
        
        # 查找該設備的激活碼
        for code, data in db.get('activation_codes', {}).items():
            if data.get('used_by_device') == device_id:
                expires_at = data.get('expires_at')
                if expires_at:
                    expire_time = datetime.fromisoformat(expires_at)
                    if datetime.now() < expire_time:
                        remaining_days = (expire_time - datetime.now()).days + 1
                        return {
                            "activated": True,
                            "plan_type": data.get('plan_type'),
                            "remaining_days": remaining_days,
                            "expires_at": expires_at
                        }
        
        return {"activated": False}
        
    except Exception as e:
        logger.error(f"狀態檢查出錯: {e}")
        raise HTTPException(status_code=500, detail="服務器錯誤")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)