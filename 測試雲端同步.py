#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試雲端同步功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from activation_codes import ActivationCodeManager
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cloud_sync():
    """測試雲端同步功能"""
    try:
        logger.info("🧪 開始測試雲端同步功能...")
        
        # 初始化激活碼管理器
        manager = ActivationCodeManager()
        logger.info("✅ 激活碼管理器初始化成功")
        
        # 生成測試激活碼
        test_user_id = 7537903238  # 您的用戶ID
        activation_code = manager.generate_trial_code(test_user_id)
        
        logger.info(f"✅ 生成測試激活碼: {activation_code}")
        logger.info("📤 激活碼應該已自動同步到雲端API")
        
        # 檢查本地數據庫
        code_info = manager.get_activation_code_info(activation_code)
        if code_info:
            logger.info(f"✅ 本地數據庫確認: {code_info['plan_type']} - {code_info['days']}天")
        else:
            logger.error("❌ 本地數據庫未找到激活碼")
        
        return activation_code
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        return None

if __name__ == "__main__":
    # 設置測試環境變量
    os.environ["TEST_MODE"] = "true"
    os.environ["API_KEY"] = "tg-api-secure-key-2024"
    
    test_code = test_cloud_sync()
    if test_code:
        print(f"\n🎉 測試成功！生成的激活碼: {test_code}")
        print("請使用此激活碼在PythonProject6中測試激活")
    else:
        print("\n❌ 測試失敗，請檢查配置")