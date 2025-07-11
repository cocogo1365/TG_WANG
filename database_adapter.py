#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫適配器 - 統一JSON和PostgreSQL接口
"""

import json
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

class DatabaseAdapter:
    """數據庫適配器 - 支持JSON和PostgreSQL"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_url = os.getenv("DATABASE_URL")
        self.json_path = os.getenv("DB_PATH", "bot_database.json")
        
        # 如果有DATABASE_URL且有psycopg2模塊就使用PostgreSQL，否則使用JSON
        self.use_postgres = bool(self.db_url) and HAS_PSYCOPG2
        
        if self.use_postgres:
            self.logger.info("使用PostgreSQL數據庫")
            self._init_postgres()
        else:
            if not HAS_PSYCOPG2:
                self.logger.warning("psycopg2模塊未安裝，使用JSON文件數據庫")
            else:
                self.logger.info("使用JSON文件數據庫")
    
    def _init_postgres(self):
        """初始化PostgreSQL表結構"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # 創建激活碼表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activation_codes (
                    code VARCHAR(50) PRIMARY KEY,
                    plan_type VARCHAR(20),
                    days INTEGER,
                    expires_at TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE,
                    used_at TIMESTAMP,
                    used_by_device VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50)
                )
            """)
            
            # 創建訂單表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(100) UNIQUE,
                    user_id VARCHAR(50),
                    plan_type VARCHAR(20),
                    amount DECIMAL(10, 2),
                    status VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            
            self.logger.info("PostgreSQL表結構初始化完成")
        except Exception as e:
            self.logger.error(f"PostgreSQL初始化失敗: {e}")
            # 降級到JSON模式
            self.use_postgres = False
    
    def get_activation_codes(self) -> Dict:
        """獲取所有激活碼"""
        if self.use_postgres:
            return self._get_activation_codes_postgres()
        else:
            return self._get_activation_codes_json()
    
    def _get_activation_codes_postgres(self) -> Dict:
        """從PostgreSQL獲取激活碼"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("SELECT * FROM activation_codes")
            rows = cur.fetchall()
            
            activation_codes = {}
            for row in rows:
                activation_codes[row['code']] = {
                    'plan_type': row['plan_type'],
                    'days': row['days'],
                    'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                    'used': row['used'],
                    'used_at': row['used_at'].isoformat() if row['used_at'] else None,
                    'used_by_device': row['used_by_device'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'created_by': row['created_by']
                }
            
            cur.close()
            conn.close()
            
            return {"activation_codes": activation_codes}
        except Exception as e:
            self.logger.error(f"PostgreSQL查詢失敗: {e}")
            return {"activation_codes": {}}
    
    def _get_activation_codes_json(self) -> Dict:
        """從JSON文件獲取激活碼"""
        try:
            if os.path.exists(self.json_path):
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"activation_codes": {}}
        except Exception as e:
            self.logger.error(f"JSON讀取失敗: {e}")
            return {"activation_codes": {}}
    
    def save_activation_code(self, code: str, data: Dict) -> bool:
        """保存激活碼"""
        if self.use_postgres:
            return self._save_activation_code_postgres(code, data)
        else:
            return self._save_activation_code_json(code, data)
    
    def _save_activation_code_postgres(self, code: str, data: Dict) -> bool:
        """保存激活碼到PostgreSQL"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # 插入或更新激活碼
            cur.execute("""
                INSERT INTO activation_codes 
                (code, plan_type, days, expires_at, used, used_at, used_by_device, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    plan_type = EXCLUDED.plan_type,
                    days = EXCLUDED.days,
                    expires_at = EXCLUDED.expires_at,
                    used = EXCLUDED.used,
                    used_at = EXCLUDED.used_at,
                    used_by_device = EXCLUDED.used_by_device
            """, (
                code,
                data.get('plan_type'),
                data.get('days'),
                datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
                data.get('used', False),
                datetime.fromisoformat(data['used_at']) if data.get('used_at') else None,
                data.get('used_by_device'),
                data.get('created_by', 'bot')
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL保存失敗: {e}")
            return False
    
    def _save_activation_code_json(self, code: str, data: Dict) -> bool:
        """保存激活碼到JSON文件"""
        try:
            # 讀取現有數據
            db_data = self._get_activation_codes_json()
            
            # 更新激活碼
            db_data["activation_codes"][code] = data
            
            # 寫入文件
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"JSON保存失敗: {e}")
            return False
    
    def update_activation_code_usage(self, code: str, device_id: str) -> bool:
        """標記激活碼為已使用"""
        if self.use_postgres:
            return self._update_activation_code_usage_postgres(code, device_id)
        else:
            return self._update_activation_code_usage_json(code, device_id)
    
    def _update_activation_code_usage_postgres(self, code: str, device_id: str) -> bool:
        """在PostgreSQL中標記激活碼為已使用"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE activation_codes 
                SET used = TRUE, used_at = CURRENT_TIMESTAMP, used_by_device = %s
                WHERE code = %s
            """, (device_id, code))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL更新失敗: {e}")
            return False
    
    def _update_activation_code_usage_json(self, code: str, device_id: str) -> bool:
        """在JSON文件中標記激活碼為已使用"""
        try:
            db_data = self._get_activation_codes_json()
            
            if code in db_data["activation_codes"]:
                db_data["activation_codes"][code]["used"] = True
                db_data["activation_codes"][code]["used_at"] = datetime.now().isoformat()
                db_data["activation_codes"][code]["used_by_device"] = device_id
                
                with open(self.json_path, 'w', encoding='utf-8') as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=2)
                
                return True
            return False
        except Exception as e:
            self.logger.error(f"JSON更新失敗: {e}")
            return False
    
    def get_activation_code(self, code: str) -> Optional[Dict]:
        """獲取單個激活碼"""
        data = self.get_activation_codes()
        return data.get("activation_codes", {}).get(code)