#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活碼管理模塊
"""

import random
import string
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from config import Config
from database import Database

logger = logging.getLogger(__name__)

class ActivationCodeManager:
    """激活碼管理器"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database()
        
        # 雲端同步配置
        self.api_url = "https://tgwang-production.up.railway.app"
        self.api_key = os.getenv("API_KEY", "tg-api-secure-key-2024")
        self.enable_cloud_sync = True
        
        logger.info(f"激活碼管理器初始化 - 雲端同步: {'啟用' if self.enable_cloud_sync else '關閉'}")
    
    def _sync_to_cloud(self, activation_code: str, code_data: Dict) -> bool:
        """同步激活碼到雲端"""
        if not self.enable_cloud_sync:
            return True
            
        try:
            sync_data = {
                "activation_code": activation_code,
                "code_data": code_data
            }
            
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
                logger.warning(f"⚠️ 雲端同步失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ 雲端同步錯誤: {e}")
            return False
    
    def generate_activation_code(self, plan_type: str, days: int, user_id: int, 
                               order_id: str = None) -> str:
        """生成激活碼"""
        
        # 生成隨機激活碼
        code = self.generate_random_code()
        
        # 計算過期時間
        expires_at = datetime.now() + timedelta(days=days)
        
        # 創建激活碼數據
        code_data = {
            'activation_code': code,
            'plan_type': plan_type,
            'user_id': user_id,
            'order_id': order_id,
            'days': days,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'used': False,
            'used_at': None,
            'used_by_device': None
        }
        
        # 保存到數據庫
        self.db.save_activation_code(code_data)
        
        # 同步到雲端
        self._sync_to_cloud(code, code_data)
        
        return code
    
    def generate_random_code(self) -> str:
        """生成隨機激活碼"""
        # 使用字母和數字，避免容易混淆的字符
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
        
        code = ''.join(random.choices(chars, k=self.config.ACTIVATION_CODE_LENGTH))
        
        # 確保激活碼唯一
        while self.db.get_activation_code(code):
            code = ''.join(random.choices(chars, k=self.config.ACTIVATION_CODE_LENGTH))
        
        return code
    
    def validate_activation_code(self, activation_code: str) -> Dict:
        """驗證激活碼"""
        result = {
            'valid': False,
            'message': '',
            'data': None
        }
        
        # 獲取激活碼數據
        code_data = self.db.get_activation_code(activation_code)
        if not code_data:
            result['message'] = '激活碼不存在'
            return result
        
        # 檢查是否已使用
        if code_data['used']:
            result['message'] = f"激活碼已於 {code_data['used_at']} 使用過"
            return result
        
        # 檢查是否過期
        expires_at = datetime.fromisoformat(code_data['expires_at'])
        if datetime.now() > expires_at:
            result['message'] = f"激活碼已於 {expires_at.strftime('%Y-%m-%d %H:%M:%S')} 過期"
            return result
        
        # 激活碼有效
        result['valid'] = True
        result['message'] = '激活碼有效'
        result['data'] = code_data
        
        return result
    
    def use_activation_code(self, activation_code: str, device_info: str = None) -> bool:
        """使用激活碼"""
        # 先驗證激活碼
        validation = self.validate_activation_code(activation_code)
        if not validation['valid']:
            return False
        
        # 標記為已使用
        code_data = validation['data']
        code_data['used'] = True
        code_data['used_at'] = datetime.now().isoformat()
        code_data['used_by_device'] = device_info
        
        # 更新數據庫
        self.db.save_activation_code(code_data)
        
        return True
    
    def get_activation_code_info(self, activation_code: str) -> Optional[Dict]:
        """獲取激活碼詳細信息"""
        return self.db.get_activation_code(activation_code)
    
    def get_activation_code_by_order(self, order_id: str) -> Optional[str]:
        """根據訂單ID獲取激活碼"""
        return self.db.get_activation_code_by_order(order_id)
    
    def generate_trial_code(self, user_id: int) -> str:
        """生成試用激活碼"""
        return self.generate_activation_code(
            plan_type='trial',
            days=2,
            user_id=user_id
        )
    
    def generate_weekly_code(self, user_id: int, order_id: str) -> str:
        """生成週卡激活碼"""
        return self.generate_activation_code(
            plan_type='weekly',
            days=7,
            user_id=user_id,
            order_id=order_id
        )
    
    def generate_monthly_code(self, user_id: int, order_id: str) -> str:
        """生成月卡激活碼"""
        return self.generate_activation_code(
            plan_type='monthly',
            days=30,
            user_id=user_id,
            order_id=order_id
        )
    
    def get_user_activation_codes(self, user_id: int) -> list:
        """獲取用戶的所有激活碼"""
        user_codes = []
        
        for code, data in self.db.data['activation_codes'].items():
            if data['user_id'] == user_id:
                user_codes.append({
                    'code': code,
                    'plan_type': data['plan_type'],
                    'days': data['days'],
                    'created_at': data['created_at'],
                    'expires_at': data['expires_at'],
                    'used': data['used'],
                    'used_at': data.get('used_at')
                })
        
        # 按創建時間排序
        user_codes.sort(key=lambda x: x['created_at'], reverse=True)
        
        return user_codes
    
    def cleanup_expired_codes(self) -> int:
        """清理過期的激活碼"""
        current_time = datetime.now()
        expired_count = 0
        
        for code, data in self.db.data['activation_codes'].items():
            if not data['used']:
                expires_at = datetime.fromisoformat(data['expires_at'])
                if current_time > expires_at:
                    # 標記為過期而不是刪除，保留記錄
                    data['expired'] = True
                    expired_count += 1
        
        if expired_count > 0:
            self.db._save_data()
        
        return expired_count
    
    def get_activation_statistics(self) -> Dict:
        """獲取激活碼統計"""
        stats = {
            'total': 0,
            'trial': 0,
            'weekly': 0,
            'monthly': 0,
            'used': 0,
            'expired': 0,
            'active': 0
        }
        
        current_time = datetime.now()
        
        for code, data in self.db.data['activation_codes'].items():
            stats['total'] += 1
            stats[data['plan_type']] += 1
            
            if data['used']:
                stats['used'] += 1
            else:
                expires_at = datetime.fromisoformat(data['expires_at'])
                if current_time > expires_at:
                    stats['expired'] += 1
                else:
                    stats['active'] += 1
        
        return stats