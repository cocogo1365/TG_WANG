#!/usr/bin/env python3
"""
診斷上傳問題
"""
import requests
import json
from datetime import datetime

# 直接測試與測試5.py相同格式的數據
test_data = {
    "activation_code": "SHOW1365",
    "device_id": "test5_py_device",
    "device_info": {
        "hostname": "TestPC",
        "platform": "Windows"
    },
    "ip_location": {
        "city": "測試城市",
        "country": "測試國家"
    },
    "group_info": {
        "name": "japanfuzoku測試",
        "link": "https://t.me/japanfuzoku"
    },
    "members": [
        {"id": 1001, "username": "test_user1", "first_name": "測試1"},
        {"id": 1002, "username": "test_user2", "first_name": "測試2"},
        {"id": 1003, "username": "test_user3", "first_name": "測試3"},
        {"id": 1004, "username": "test_user4", "first_name": "測試4"},
        {"id": 1005, "username": "test_user5", "first_name": "測試5"}
    ]
}

print("=== 診斷測試5.py上傳問題 ===")
print(f"時間: {datetime.now()}")

# 測試上傳
url = "https://tgwang.up.railway.app/api/upload_collection_data"
response = requests.post(url, json=test_data)

print(f"\n響應狀態: {response.status_code}")
print(f"響應內容: {response.text}")

if response.status_code == 200:
    result = response.json()
    print(f"\n存儲位置: {result.get('storage', '未知')}")
    
    if result.get('storage') == 'filesystem':
        print("⚠️ 數據保存到文件系統（非PostgreSQL）")
        print("可能原因：")
        print("1. DATABASE_URL 未設置")
        print("2. PostgreSQL 連接失敗")
        print("3. 表創建失敗")
    elif result.get('storage') == 'postgresql':
        print("✅ 數據已保存到 PostgreSQL")

# 檢查 API 健康狀態
health_response = requests.get("https://tgwang.up.railway.app/api/health")
print(f"\n健康檢查: {health_response.status_code}")

print("\n請在 TablePlus 中執行以下 SQL 查詢：")
print("SELECT * FROM collection_data WHERE device_id = 'test5_py_device';")