#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
啟用雲端同步 - 修改activation_codes.py以支持自動雲端同步
"""

import os

def enable_cloud_sync():
    """修改activation_codes.py以啟用雲端同步"""
    
    # 讀取現有的activation_codes.py
    with open('activation_codes.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在文件開頭添加導入
    imports = """import requests
import logging
from typing import Dict

logger = logging.getLogger(__name__)
"""
    
    # 添加雲端同步方法
    sync_method = '''
    def _sync_to_cloud(self, activation_code: str, code_data: Dict):
        """同步激活碼到雲端"""
        try:
            api_url = "https://tgwang-production.up.railway.app"
            api_key = "tg-api-secure-key-2024"
            
            sync_data = {
                "activation_code": activation_code,
                "code_data": code_data
            }
            
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{api_url}/sync/activation_code",
                json=sync_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ 激活碼 {activation_code} 已同步到雲端")
            else:
                logger.warning(f"⚠️ 雲端同步失敗: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ 雲端同步錯誤: {e}")
            # 不影響本地保存
'''
    
    # 在generate_activation_code方法的save_activation_code後添加同步
    if '# 保存到數據庫' in content:
        # 找到保存數據庫的位置
        save_position = content.find('self.db.save_activation_code(code_data)')
        if save_position > 0:
            # 在保存後添加同步
            insert_position = content.find('\n', save_position) + 1
            sync_call = '''        
        # 同步到雲端
        self._sync_to_cloud(code, code_data)
'''
            content = content[:insert_position] + sync_call + content[insert_position:]
    
    # 添加同步方法到類中
    class_end_position = content.rfind('def generate_trial_code')
    if class_end_position > 0:
        content = content[:class_end_position] + sync_method + '\n    ' + content[class_end_position:]
    
    # 添加導入
    if 'import requests' not in content:
        content = imports + '\n' + content
    
    # 保存修改後的文件
    with open('activation_codes_with_sync.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已創建支持雲端同步的activation_codes_with_sync.py")
    print("請將activation_codes.py備份，然後用activation_codes_with_sync.py替換它")
    
    return True

if __name__ == "__main__":
    enable_cloud_sync()