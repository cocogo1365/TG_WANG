#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雲端同步客戶端 - 供主軟件使用
讓TG旺主軟件直接從雲端API驗證激活碼
"""

import requests
import json
import logging
from typing import Dict, Optional
from datetime import datetime

class CloudSyncClient:
    """雲端同步客戶端"""
    
    def __init__(self):
        # 雲端API配置
        self.api_url = "https://tgwang.up.railway.app"
        self.api_key = "tg-api-secure-key-2024"
        self.timeout = 10
        
        # 設置日誌
        self.logger = logging.getLogger(__name__)
    
    def _get_headers(self) -> Dict[str, str]:
        """獲取請求頭"""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "TGWang-Software/1.0"
        }
    
    def verify_activation_code_cloud(self, activation_code: str, device_id: str = None) -> Dict:
        """從雲端驗證激活碼"""
        try:
            # 準備請求數據
            request_data = {
                "activation_code": activation_code,
                "device_id": device_id or "unknown",
                "timestamp": datetime.now().isoformat()
            }
            
            # 調用雲端API
            response = requests.post(
                f"{self.api_url}/api/verify_activation",
                json=request_data,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ 雲端驗證成功: {activation_code}")
                return {
                    "success": True,
                    "valid": result.get("valid", False),
                    "message": result.get("message", "驗證成功"),
                    "data": result.get("data", {}),
                    "source": "cloud"
                }
            else:
                error_msg = f"API錯誤 {response.status_code}: {response.text}"
                self.logger.error(f"❌ 雲端驗證失敗: {error_msg}")
                return {
                    "success": False,
                    "valid": False,
                    "message": error_msg,
                    "source": "cloud_error"
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"網路連線錯誤: {str(e)}"
            self.logger.error(f"❌ 雲端連線失敗: {error_msg}")
            return {
                "success": False,
                "valid": False,
                "message": error_msg,
                "source": "network_error"
            }
        except Exception as e:
            error_msg = f"未知錯誤: {str(e)}"
            self.logger.error(f"❌ 雲端驗證異常: {error_msg}")
            return {
                "success": False,
                "valid": False,
                "message": error_msg,
                "source": "unknown_error"
            }
    
    def use_activation_code_cloud(self, activation_code: str, device_id: str) -> Dict:
        """使用激活碼（標記為已使用）"""
        try:
            request_data = {
                "activation_code": activation_code,
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.api_url}/api/use_activation",
                json=request_data,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ 激活碼使用成功: {activation_code}")
                return {
                    "success": True,
                    "message": result.get("message", "激活成功"),
                    "data": result.get("data", {}),
                    "source": "cloud"
                }
            else:
                error_msg = f"使用失敗 {response.status_code}: {response.text}"
                self.logger.error(f"❌ 激活碼使用失敗: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "source": "cloud_error"
                }
                
        except Exception as e:
            error_msg = f"使用激活碼時發生錯誤: {str(e)}"
            self.logger.error(f"❌ 使用激活碼異常: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "source": "error"
            }
    
    def get_user_activation_codes_cloud(self, user_id: int) -> Dict:
        """獲取用戶的激活碼列表"""
        try:
            response = requests.get(
                f"{self.api_url}/api/user/{user_id}/activation_codes",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "codes": result.get("codes", []),
                    "source": "cloud"
                }
            else:
                return {
                    "success": False,
                    "codes": [],
                    "message": f"獲取失敗: {response.status_code}",
                    "source": "cloud_error"
                }
                
        except Exception as e:
            return {
                "success": False,
                "codes": [],
                "message": f"連線錯誤: {str(e)}",
                "source": "error"
            }
    
    def test_cloud_connection(self) -> Dict:
        """測試雲端連線"""
        try:
            response = requests.get(
                f"{self.api_url}/api/health",
                headers=self._get_headers(),
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "雲端連線正常",
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "message": f"雲端服務異常: {response.status_code}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"連線失敗: {str(e)}",
                "status_code": 0
            }

class HybridActivationValidator:
    """混合激活驗證器 - 優先雲端，本地備用"""
    
    def __init__(self, local_db_path: str = "bot_database.json"):
        self.cloud_client = CloudSyncClient()
        self.local_db_path = local_db_path
        self.logger = logging.getLogger(__name__)
    
    def _load_local_database(self) -> Dict:
        """加載本地資料庫"""
        try:
            with open(self.local_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"activation_codes": {}}
    
    def _validate_local(self, activation_code: str) -> Dict:
        """本地驗證激活碼"""
        try:
            data = self._load_local_database()
            code_info = data.get("activation_codes", {}).get(activation_code)
            
            if not code_info:
                return {
                    "valid": False,
                    "message": "激活碼不存在（本地）",
                    "source": "local"
                }
            
            if code_info.get("used", False):
                return {
                    "valid": False,
                    "message": f"激活碼已使用過（{code_info.get('used_at', 'unknown')}）",
                    "source": "local"
                }
            
            # 檢查過期
            expires_at = datetime.fromisoformat(code_info["expires_at"])
            if datetime.now() > expires_at:
                return {
                    "valid": False,
                    "message": f"激活碼已過期（{expires_at.strftime('%Y-%m-%d')}）",
                    "source": "local"
                }
            
            return {
                "valid": True,
                "message": "激活碼有效（本地）",
                "data": code_info,
                "source": "local"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"本地驗證錯誤: {str(e)}",
                "source": "local_error"
            }
    
    def validate_activation_code(self, activation_code: str, device_id: str = None) -> Dict:
        """混合驗證激活碼（優先雲端）"""
        self.logger.info(f"🔍 開始驗證激活碼: {activation_code}")
        
        # 1. 首先嘗試雲端驗證
        cloud_result = self.cloud_client.verify_activation_code_cloud(activation_code, device_id)
        
        if cloud_result["success"]:
            self.logger.info("✅ 雲端驗證成功")
            return cloud_result
        
        # 2. 雲端失敗，使用本地備用驗證
        self.logger.warning("⚠️ 雲端驗證失敗，嘗試本地驗證")
        local_result = self._validate_local(activation_code)
        
        return {
            "success": local_result["valid"],
            "valid": local_result["valid"],
            "message": f"{local_result['message']} [雲端不可用: {cloud_result['message']}]",
            "data": local_result.get("data", {}),
            "source": local_result["source"],
            "cloud_error": cloud_result["message"]
        }
    
    def use_activation_code(self, activation_code: str, device_id: str) -> Dict:
        """使用激活碼"""
        # 先驗證
        validation_result = self.validate_activation_code(activation_code, device_id)
        
        if not validation_result["valid"]:
            return {
                "success": False,
                "message": f"激活碼無效: {validation_result['message']}"
            }
        
        # 嘗試雲端使用
        cloud_use_result = self.cloud_client.use_activation_code_cloud(activation_code, device_id)
        
        if cloud_use_result["success"]:
            return cloud_use_result
        
        # 雲端失敗，本地使用（需要實現本地使用邏輯）
        return {
            "success": False,
            "message": f"雲端激活失敗: {cloud_use_result['message']}"
        }

# 測試函數
def test_cloud_sync():
    """測試雲端同步功能"""
    print("🧪 測試雲端同步功能...")
    
    # 測試連線
    client = CloudSyncClient()
    connection_test = client.test_cloud_connection()
    print(f"連線測試: {connection_test}")
    
    # 測試激活碼驗證
    test_codes = [
        "6BMLQHT7NGM3TY9J",
        "N7BFM2X8GVHPQW4K",
        "FREETRIAL2025ABC"
    ]
    
    validator = HybridActivationValidator()
    
    for code in test_codes:
        print(f"\n測試激活碼: {code}")
        result = validator.validate_activation_code(code, "test-device-123")
        print(f"結果: {result['valid']} - {result['message']}")
        print(f"來源: {result.get('source', 'unknown')}")

if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_cloud_sync()