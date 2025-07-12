#!/usr/bin/env python3
"""
測試基本 API 連接
"""
import requests

# 測試不同的端點
urls = [
    "https://tgwang.up.railway.app/",
    "https://tgwang.up.railway.app/dashboard",
    "https://tgwang.up.railway.app/api/dashboard",
    "https://tgwang.up.railway.app/api/orders",
    "https://tgwang.up.railway.app/api/upload_collection_data"
]

print("=== 測試 Railway 應用連接 ===\n")

for url in urls:
    try:
        if "upload_collection_data" in url:
            # POST 請求
            response = requests.post(url, json={}, timeout=5)
        else:
            # GET 請求
            response = requests.get(url, timeout=5)
        
        print(f"✓ {url}")
        print(f"  狀態碼: {response.status_code}")
        
        # 顯示部分響應內容
        if response.status_code == 200:
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"  類型: JSON")
            else:
                print(f"  類型: HTML")
        elif response.status_code == 400:
            print(f"  響應: {response.text[:100]}...")
        elif response.status_code == 404:
            print(f"  ❌ 端點不存在")
            
    except Exception as e:
        print(f"✗ {url}")
        print(f"  錯誤: {e}")
    
    print()

print("\n如果 /api/upload_collection_data 返回 404，表示新代碼還沒部署。")