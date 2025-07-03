#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TronGrid API 連接測試工具
"""

import os
import asyncio
import sys

def test_environment():
    """測試環境變量"""
    print("🔧 檢查環境變量...")
    
    required_vars = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'USDT_ADDRESS': os.getenv('USDT_ADDRESS'),
        'TRONGRID_API_KEY': os.getenv('TRONGRID_API_KEY'),
        'TEST_MODE': os.getenv('TEST_MODE')
    }
    
    all_set = True
    for var, value in required_vars.items():
        if value:
            display_value = f"{value[:8]}..." if var in ['BOT_TOKEN', 'TRONGRID_API_KEY'] else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: 未設置")
            all_set = False
    
    return all_set

async def test_api_with_requests():
    """使用 requests 測試 API (如果可用)"""
    try:
        import requests
        print("\n🌐 使用 requests 測試 TronGrid API...")
        
        api_key = os.getenv('TRONGRID_API_KEY')
        if not api_key:
            print("❌ TRONGRID_API_KEY 未設置，跳過測試")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'TRON-PRO-API-KEY': api_key
        }
        
        url = "https://api.trongrid.io/wallet/getnowblock"
        
        print(f"📡 發送請求到: {url}")
        print(f"🔑 使用 API 密鑰: {api_key[:8]}...")
        
        try:
            response = requests.post(url, headers=headers, timeout=15)
            print(f"📊 響應狀態: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                block_num = data.get('block_header', {}).get('raw_data', {}).get('number', 0)
                print(f"✅ API 連接成功!")
                print(f"📊 當前區塊: {block_num}")
                return True
            elif response.status_code == 403:
                print("❌ API 密鑰無效或權限不足")
                print("🔍 請檢查 tronscan.org 上的 API 密鑰是否正確")
                return False
            elif response.status_code == 429:
                print("❌ API 請求頻率限制")
                print("🔍 請稍後重試或檢查 API 計畫")
                return False
            else:
                print(f"❌ API 請求失敗: {response.status_code}")
                try:
                    print(f"錯誤信息: {response.text[:200]}")
                except:
                    pass
                return False
                
        except requests.exceptions.Timeout:
            print("⏰ API 請求超時")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ 網絡連接錯誤")
            return False
        except Exception as e:
            print(f"❌ 請求異常: {e}")
            return False
            
    except ImportError:
        print("⚠️ requests 模塊未安裝，跳過 API 測試")
        return None

async def test_api_with_aiohttp():
    """使用 aiohttp 測試 API (機器人實際使用的方法)"""
    try:
        import aiohttp
        print("\n🌐 使用 aiohttp 測試 TronGrid API...")
        
        api_key = os.getenv('TRONGRID_API_KEY')
        if not api_key:
            print("❌ TRONGRID_API_KEY 未設置，跳過測試")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'TRON-PRO-API-KEY': api_key
        }
        
        url = "https://api.trongrid.io/wallet/getnowblock"
        
        print(f"📡 發送異步請求到: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as response:
                    print(f"📊 響應狀態: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        block_num = data.get('block_header', {}).get('raw_data', {}).get('number', 0)
                        print(f"✅ aiohttp API 連接成功!")
                        print(f"📊 當前區塊: {block_num}")
                        return True
                    else:
                        print(f"❌ aiohttp API 請求失敗: {response.status}")
                        try:
                            error_text = await response.text()
                            print(f"錯誤信息: {error_text[:200]}")
                        except:
                            pass
                        return False
                        
        except asyncio.TimeoutError:
            print("⏰ aiohttp 請求超時")
            return False
        except aiohttp.ClientError as e:
            print(f"❌ aiohttp 客戶端錯誤: {e}")
            return False
        except Exception as e:
            print(f"❌ aiohttp 異常: {e}")
            return False
            
    except ImportError:
        print("⚠️ aiohttp 模塊未安裝，跳過異步 API 測試")
        return None

def test_bot_startup():
    """測試機器人啟動過程"""
    print("\n🤖 測試機器人組件初始化...")
    
    try:
        from config import Config
        config = Config()
        print("✅ Config 初始化成功")
        print(f"🔑 API URL: {config.TRONGRID_API_URL}")
        print(f"📧 錢包地址: {config.USDT_ADDRESS}")
        
        from database import Database
        db = Database()
        print("✅ Database 初始化成功")
        
        # 不測試 TronMonitor，因為需要 aiohttp
        print("⚠️ 跳過 TronMonitor 測試 (需要 aiohttp)")
        
        return True
        
    except Exception as e:
        print(f"❌ 機器人組件初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主測試函數"""
    print("🚀 TronGrid API 連接診斷工具")
    print("="*50)
    
    # 測試環境變量
    env_ok = test_environment()
    if not env_ok:
        print("\n❌ 環境變量配置有問題，請先修復")
        return
    
    print("\n" + "="*50)
    
    # 測試機器人啟動
    bot_ok = test_bot_startup()
    
    print("\n" + "="*50)
    
    # 測試 API 連接
    api_ok = await test_api_with_requests()
    if api_ok is None:
        api_ok = await test_api_with_aiohttp()
    
    print("\n" + "="*50)
    print("🏁 診斷結果:")
    print(f"環境變量: {'✅' if env_ok else '❌'}")
    print(f"機器人組件: {'✅' if bot_ok else '❌'}")
    print(f"API 連接: {'✅' if api_ok else '❌' if api_ok is not None else '⚠️ 無法測試'}")
    
    if api_ok is False:
        print("\n🔧 建議解決方案:")
        print("1. 檢查 TRONGRID_API_KEY 是否正確")
        print("2. 確認 API 密鑰在 tronscan.org 上是否有效")
        print("3. 檢查 API 密鑰的使用額度")
        print("4. 嘗試重新生成 API 密鑰")

if __name__ == "__main__":
    asyncio.run(main())