#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG激活碼API服務 - Railway部署版 (備份文件)
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
from datetime import datetime
import logging

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
DB_PATH = os.getenv("DB_PATH", "bot_database.json")

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
            "health": "/health"
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

# 其他原有的API端點...