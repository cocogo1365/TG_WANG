#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG旺軟件激活客戶端
供主軟件使用，實現雲端激活碼驗證
"""

import requests
import json
import logging
import os
from typing import Dict, Optional
from datetime import datetime

class TGWangActivationClient:
    """TG旺軟件激活客戶端"""
    
    def __init__(self, local_db_path: str = None):
        # 本地資料庫路徑
        if local_db_path:
            self.local_db_path = local_db_path
        else:
            # 自動尋找資料庫檔案
            possible_paths = [
                "bot_database.json",
                "../TG_WANG/bot_database.json",
                "C:/Users/XX11/Documents/GitHub/TG_WANG/bot_database.json",
                "/mnt/c/Users/XX11/Documents/GitHub/TG_WANG/bot_database.json"
            ]
            self.local_db_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    self.local_db_path = path
                    break
        
        # 雲端API配置（備用）
        self.api_url = "https://tgwang.up.railway.app"
        self.api_key = "tg-api-secure-key-2024"
        
        # 設置日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"TG旺激活客戶端初始化")
        self.logger.info(f"本地資料庫: {self.local_db_path}")
    
    def _load_local_database(self) -> Dict:
        """加載本地資料庫"""
        try:
            if not self.local_db_path or not os.path.exists(self.local_db_path):
                self.logger.warning("本地資料庫檔案不存在")
                return {"activation_codes": {}}
            
            with open(self.local_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.logger.info(f"本地資料庫載入成功，激活碼數量: {len(data.get('activation_codes', {}))}")
                return data
        except Exception as e:
            self.logger.error(f"載入本地資料庫失敗: {e}")
            return {"activation_codes": {}}
    
    def _save_local_database(self, data: Dict) -> bool:
        """保存本地資料庫"""
        try:
            if not self.local_db_path:
                return False
            
            with open(self.local_db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("本地資料庫保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存本地資料庫失敗: {e}")
            return False
    
    def validate_activation_code(self, activation_code: str) -> Dict:
        """驗證激活碼"""
        self.logger.info(f"🔍 驗證激活碼: {activation_code}")
        
        # 加載本地資料庫
        data = self._load_local_database()
        code_info = data.get("activation_codes", {}).get(activation_code)
        
        if not code_info:
            return {
                "valid": False,
                "message": "激活碼不存在",
                "source": "local"
            }
        
        if code_info.get("used", False):
            used_at = code_info.get('used_at', 'unknown')
            used_device = code_info.get('used_by_device', 'unknown')
            return {
                "valid": False,
                "message": f"激活碼已使用過\\n使用時間: {used_at}\\n使用設備: {used_device}",
                "source": "local"
            }
        
        # 檢查過期
        try:
            expires_at = datetime.fromisoformat(code_info["expires_at"])
            if datetime.now() > expires_at:
                return {
                    "valid": False,
                    "message": f"激活碼已過期\\n過期時間: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    "source": "local"
                }
        except:
            pass
        
        return {
            "valid": True,
            "message": "激活碼有效",
            "data": code_info,
            "source": "local"
        }
    
    def use_activation_code(self, activation_code: str, device_id: str = "unknown") -> Dict:
        """使用激活碼（激活軟件）"""
        self.logger.info(f"🎯 使用激活碼: {activation_code}")
        
        # 先驗證激活碼
        validation_result = self.validate_activation_code(activation_code)
        if not validation_result["valid"]:
            return {
                "success": False,
                "message": validation_result["message"]
            }
        
        # 標記為已使用
        data = self._load_local_database()
        code_info = data["activation_codes"][activation_code]
        
        code_info["used"] = True
        code_info["used_at"] = datetime.now().isoformat()
        code_info["used_by_device"] = device_id
        
        # 保存更新
        if self._save_local_database(data):
            plan_name = {
                'trial': '試用版',
                'weekly': '週方案',
                'monthly': '月方案'
            }.get(code_info['plan_type'], code_info['plan_type'])
            
            return {
                "success": True,
                "message": f"激活成功！\\n方案: {plan_name}\\n有效期: {code_info['days']}天",
                "data": {
                    "plan_type": code_info['plan_type'],
                    "days": code_info['days'],
                    "expires_at": code_info['expires_at'],
                    "used_at": code_info['used_at']
                }
            }
        else:
            return {
                "success": False,
                "message": "激活失敗：無法保存激活狀態"
            }
    
    def get_activation_status(self, activation_code: str) -> Dict:
        """獲取激活碼狀態"""
        validation_result = self.validate_activation_code(activation_code)
        
        if validation_result["valid"]:
            code_info = validation_result["data"]
            return {
                "exists": True,
                "used": code_info.get("used", False),
                "plan_type": code_info.get("plan_type"),
                "days": code_info.get("days"),
                "expires_at": code_info.get("expires_at"),
                "used_at": code_info.get("used_at"),
                "used_by_device": code_info.get("used_by_device")
            }
        else:
            return {
                "exists": False,
                "message": validation_result["message"]
            }
    
    def test_connection(self) -> Dict:
        """測試連線狀態"""
        result = {
            "local_db": False,
            "cloud_api": False,
            "message": []
        }
        
        # 測試本地資料庫
        if self.local_db_path and os.path.exists(self.local_db_path):
            try:
                data = self._load_local_database()
                codes_count = len(data.get('activation_codes', {}))
                result["local_db"] = True
                result["message"].append(f"✅ 本地資料庫正常 ({codes_count}個激活碼)")
            except:
                result["message"].append("❌ 本地資料庫讀取失敗")
        else:
            result["message"].append("❌ 本地資料庫檔案不存在")
        
        # 測試雲端API（可選）
        try:
            response = requests.get(f"{self.api_url}/api/health", timeout=5)
            if response.status_code == 200:
                result["cloud_api"] = True
                result["message"].append("✅ 雲端API連線正常")
            else:
                result["message"].append(f"⚠️ 雲端API異常 ({response.status_code})")
        except:
            result["message"].append("⚠️ 雲端API無法連線（將使用本地模式）")
        
        return result

def demo_usage():
    """演示用法"""
    print("🚀 TG旺軟件激活客戶端 - 演示")
    print("=" * 50)
    
    # 初始化客戶端
    client = TGWangActivationClient()
    
    # 測試連線
    print("\\n📡 測試連線:")
    connection_test = client.test_connection()
    for msg in connection_test["message"]:
        print(f"   {msg}")
    
    # 測試激活碼
    test_codes = [
        "6BMLQHT7NGM3TY9J",
        "N7BFM2X8GVHPQW4K", 
        "FREETRIAL2025ABC"
    ]
    
    print("\\n🔍 測試激活碼驗證:")
    for code in test_codes:
        result = client.validate_activation_code(code)
        status = "✅ 有效" if result["valid"] else "❌ 無效"
        print(f"   {code}: {status} - {result['message']}")
    
    # 演示激活過程
    print("\\n🎯 演示激活過程:")
    demo_code = "FREETRIAL2025ABC"  # 使用長期有效的測試碼
    
    print(f"使用激活碼: {demo_code}")
    activation_result = client.use_activation_code(demo_code, "DEMO-DEVICE-123")
    
    if activation_result["success"]:
        print(f"✅ {activation_result['message']}")
    else:
        print(f"❌ {activation_result['message']}")

if __name__ == "__main__":
    demo_usage()