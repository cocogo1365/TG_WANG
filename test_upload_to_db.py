#!/usr/bin/env python3
"""
測試上傳數據到 PostgreSQL
"""
import requests
import json
from datetime import datetime

# API 端點
# 修改為你的實際 Railway 應用 URL
# 格式通常是: https://你的應用名稱.up.railway.app
API_URL = "https://tg-wang.up.railway.app/api/upload_collection_data"  # 請確認你的實際 URL

# 測試數據
test_data = {
    "activation_code": "SHOW1365",
    "device_id": "test_postgresql_001",
    "device_info": {
        "hostname": "TestPC-PostgreSQL",
        "platform": "Windows 10",
        "version": "測試版本"
    },
    "ip_location": {
        "ip": "1.2.3.4",
        "city": "台北",
        "country": "台灣"
    },
    "group_info": {
        "name": "PostgreSQL測試群組",
        "link": "https://t.me/test_postgresql"
    },
    "members": [
        {
            "id": 123456,
            "username": "pgtest1",
            "first_name": "測試用戶1",
            "last_name": "",
            "is_bot": False
        },
        {
            "id": 789012,
            "username": "pgtest2", 
            "first_name": "測試用戶2",
            "last_name": "",
            "is_bot": False
        },
        {
            "id": 345678,
            "username": "pgtest3",
            "first_name": "測試用戶3",
            "last_name": "",
            "is_bot": False
        }
    ]
}

def test_upload():
    """測試上傳功能"""
    print("=== 測試 PostgreSQL 上傳功能 ===")
    print(f"時間: {datetime.now()}")
    print(f"API: {API_URL}")
    print(f"激活碼: {test_data['activation_code']}")
    print(f"成員數: {len(test_data['members'])}")
    
    try:
        # 發送請求
        response = requests.post(
            API_URL,
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n響應狀態: {response.status_code}")
        print(f"響應內容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('storage') == 'postgresql':
                print("\n✅ 成功！數據已保存到 PostgreSQL")
            elif result.get('storage') == 'filesystem':
                print("\n⚠️ 警告：數據保存到文件系統（降級模式）")
            else:
                print("\n✅ 上傳成功")
        else:
            print("\n❌ 上傳失敗")
            
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")

if __name__ == "__main__":
    test_upload()
    print("\n測試完成！請到網站查看採集數據頁面。")