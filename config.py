#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模塊
"""

import os
from typing import List

class Config:
    """配置類"""
    
    def __init__(self):
        # Telegram Bot Token
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        
        # TronGrid API 配置
        self.TRONGRID_API_KEY = os.getenv('TRONGRID_API_KEY')
        self.TRONGRID_API_URL = "https://api.trongrid.io"
        
        # USDT 配置
        self.USDT_ADDRESS = os.getenv('USDT_ADDRESS', 'TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP')
        self.USDT_CONTRACT = os.getenv('USDT_CONTRACT', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')
        
        # 管理員用戶ID
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        self.ADMIN_IDS = [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip().isdigit()]
        
        # 數據庫文件路徑
        self.DATABASE_FILE = os.getenv('DATABASE_FILE', 'bot_database.json')
        
        # 監控配置
        self.MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '60'))  # 秒
        self.CONFIRMATION_BLOCKS = int(os.getenv('CONFIRMATION_BLOCKS', '1'))  # 確認區塊數
        
        # 訂單配置
        self.ORDER_TIMEOUT_HOURS = int(os.getenv('ORDER_TIMEOUT_HOURS', '24'))
        
        # 激活碼配置
        self.ACTIVATION_CODE_LENGTH = int(os.getenv('ACTIVATION_CODE_LENGTH', '16'))
        
        # 驗證配置
        self.validate_config()
    
    def validate_config(self):
        """驗證配置"""
        required_vars = ['BOT_TOKEN', 'USDT_ADDRESS']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(self, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"缺少必需的環境變量: {', '.join(missing_vars)}")
        
        # 驗證 USDT 地址格式
        if not self.USDT_ADDRESS.startswith('T') or len(self.USDT_ADDRESS) != 34:
            raise ValueError(f"無效的 USDT 地址格式: {self.USDT_ADDRESS}")
    
    def get_trongrid_headers(self) -> dict:
        """獲取 TronGrid API 請求頭"""
        headers = {'Content-Type': 'application/json'}
        if self.TRONGRID_API_KEY:
            headers['TRON-PRO-API-KEY'] = self.TRONGRID_API_KEY
        return headers