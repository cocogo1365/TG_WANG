#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手動 API 測試 - 不依賴複雜模塊
"""

import os
import json
import urllib.request
import urllib.parse

def test_api_manual():
    """手動測試 TronGrid API"""
    print("🔧 手動測試 TronGrid API...")
    
    api_key = os.getenv('TRONGRID_API_KEY')
    if not api_key:
        print("❌ TRONGRID_API_KEY 未設置")
        return False
    
    print(f"🔑 API 密鑰: {api_key[:10]}...")
    
    url = "https://apilist.tronscanapi.com/api/block"
    
    # 構建請求
    headers = {
        'Content-Type': 'application/json',
        'TRON-PRO-API-KEY': api_key
    }
    
    try:
        # 創建請求
        req = urllib.request.Request(url, headers=headers, method='GET')
        
        print(f"📡 發送請求到: {url}")
        
        # 發送請求
        with urllib.request.urlopen(req, timeout=15) as response:
            status_code = response.getcode()
            response_data = response.read()
            
            print(f"📊 響應狀態: {status_code}")
            
            if status_code == 200:
                data = json.loads(response_data.decode('utf-8'))
                # 處理可能的數組返回
                if isinstance(data, list) and len(data) > 0:
                    block_num = data[0].get('number', 0)
                elif isinstance(data, dict):
                    block_num = data.get('number', 0)
                else:
                    block_num = 0
                print(f"✅ API 連接成功!")
                print(f"📊 當前區塊: {block_num}")
                
                # 測試獲取賬戶交易
                test_account_transactions(api_key)
                
                return True
            else:
                print(f"❌ API 請求失敗: {status_code}")
                print(f"響應內容: {response_data.decode('utf-8')[:200]}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP 錯誤: {e.code}")
        if e.code == 403:
            print("🔍 API 密鑰可能無效或權限不足")
        elif e.code == 429:
            print("🔍 API 請求頻率限制")
        try:
            error_data = e.read().decode('utf-8')
            print(f"錯誤詳情: {error_data[:200]}")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"❌ 網絡錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")
        return False

def test_account_transactions(api_key):
    """測試獲取賬戶交易"""
    usdt_address = os.getenv('USDT_ADDRESS')
    if not usdt_address:
        print("⚠️ USDT_ADDRESS 未設置，跳過交易測試")
        return
    
    print(f"\n💰 測試獲取賬戶交易...")
    print(f"📧 錢包地址: {usdt_address}")
    
    url = f"https://apilist.tronscanapi.com/api/transaction"
    
    headers = {
        'TRON-PRO-API-KEY': api_key
    }
    
    # 添加查詢參數
    params = {
        'limit': 10,
        'address': usdt_address,
        'start': 0,
        'direction': 'in'
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    try:
        req = urllib.request.Request(full_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                transactions = data.get('data', [])
                print(f"✅ 成功獲取 {len(transactions)} 個交易記錄")
                
                # 顯示最近的幾個交易
                for i, tx in enumerate(transactions[:3]):
                    print(f"  交易 {i+1}: {tx.get('hash', '未知')[:16]}...")
                    
            else:
                print(f"❌ 獲取交易失敗: {response.getcode()}")
                
    except Exception as e:
        print(f"❌ 獲取交易錯誤: {e}")

def main():
    """主函數"""
    print("🚀 手動 TronGrid API 測試")
    print("="*40)
    
    # 檢查環境變量
    required_vars = ['TRONGRID_API_KEY', 'USDT_ADDRESS', 'TEST_MODE']
    for var in required_vars:
        value = os.getenv(var)
        display = f"{value[:8]}..." if var == 'TRONGRID_API_KEY' and value else value
        print(f"{var}: {display if value else '未設置'}")
    
    print("="*40)
    
    # 測試 API
    success = test_api_manual()
    
    print("="*40)
    if success:
        print("✅ API 測試成功！機器人應該能正常監控付款")
    else:
        print("❌ API 測試失敗！請檢查配置")
        print("\n🔧 建議解決方案:")
        print("1. 重新生成 TronScan API 密鑰")
        print("2. 檢查 API 密鑰權限和配額")
        print("3. 確認 Railway.com 環境變量設置正確")

if __name__ == "__main__":
    main()