#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雲端同步機器人 - 自動同步激活碼到雲端API
"""

import os
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CloudSyncManager:
    """雲端同步管理器"""
    
    def __init__(self):
        # Railway API配置
        self.api_url = "https://tgwang-production.up.railway.app"
        self.api_key = os.getenv("API_KEY", "tg-api-secure-key-2024")
        
        # 本地數據庫路徑
        self.local_db_path = "bot_database.json"
        
        logger.info(f"🌐 雲端同步管理器初始化 - API: {self.api_url}")
    
    def sync_activation_code_to_cloud(self, activation_code: str, code_data: Dict) -> bool:
        """同步激活碼到雲端"""
        try:
            # 準備同步數據
            sync_data = {
                "activation_code": activation_code,
                "code_data": code_data,
                "sync_time": datetime.now().isoformat()
            }
            
            # 發送到雲端API
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_url}/sync/activation_code",
                json=sync_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ 激活碼 {activation_code} 已同步到雲端")
                return True
            else:
                logger.error(f"❌ 雲端同步失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 雲端同步錯誤: {e}")
            # 如果雲端同步失敗，確保本地數據庫有記錄
            self.save_to_local_db(activation_code, code_data)
            return False
    
    def save_to_local_db(self, activation_code: str, code_data: Dict):
        """保存到本地數據庫"""
        try:
            # 讀取現有數據
            if os.path.exists(self.local_db_path):
                with open(self.local_db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
            else:
                db_data = {
                    "activation_codes": {},
                    "orders": {},
                    "users": {},
                    "statistics": {}
                }
            
            # 添加激活碼
            db_data['activation_codes'][activation_code] = code_data
            
            # 保存數據
            with open(self.local_db_path, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 激活碼 {activation_code} 已保存到本地數據庫")
            
        except Exception as e:
            logger.error(f"❌ 本地保存失敗: {e}")
    
    def sync_order_to_cloud(self, order_data: Dict) -> bool:
        """同步訂單到雲端"""
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_url}/sync/order",
                json=order_data,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"❌ 訂單同步錯誤: {e}")
            return False

# 整合到現有的激活碼管理器
class EnhancedActivationCodeManager:
    """增強版激活碼管理器 - 支持雲端同步"""
    
    def __init__(self, original_manager):
        self.original_manager = original_manager
        self.cloud_sync = CloudSyncManager()
    
    def generate_activation_code(self, plan_type: str, days: int, user_id: int, 
                               order_id: str = None) -> str:
        """生成激活碼並自動同步到雲端"""
        
        # 使用原始管理器生成激活碼
        activation_code = self.original_manager.generate_activation_code(
            plan_type, days, user_id, order_id
        )
        
        # 準備激活碼數據
        code_data = {
            'activation_code': activation_code,
            'plan_type': plan_type,
            'user_id': user_id,
            'order_id': order_id,
            'days': days,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=days)).isoformat(),
            'used': False,
            'used_at': None,
            'used_by_device': None
        }
        
        # 同步到雲端
        self.cloud_sync.sync_activation_code_to_cloud(activation_code, code_data)
        
        return activation_code