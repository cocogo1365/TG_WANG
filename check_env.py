#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
環境檢查腳本 - 在 Railway.com 上運行來檢查配置
"""

import os

def check_railway_env():
    """檢查 Railway.com 環境配置"""
    print("🚀 Railway.com 環境配置檢查")
    print("="*50)
    
    required_vars = {
        'BOT_TOKEN': '您的 Telegram Bot Token',
        'USDT_ADDRESS': '您的 TRON 錢包地址',
        'TRONGRID_API_KEY': '您的 TronGrid API 密鑰',
        'TEST_MODE': '測試模式 (設為 true)',
        'ADMIN_IDS': '您的 Telegram 用戶ID'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # 隱藏敏感信息
            if var in ['BOT_TOKEN', 'TRONGRID_API_KEY']:
                display_value = f"{value[:8]}..." if len(value) > 8 else "已設置"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: 未設置")
            print(f"   說明: {description}")
            missing_vars.append(var)
        print()
    
    if missing_vars:
        print("🔧 需要在 Railway.com 中設置以下環境變量:")
        print("-" * 40)
        for var in missing_vars:
            print(f"• {var} = {required_vars[var]}")
        print()
        print("📝 設置步驟:")
        print("1. 進入 Railway.com 項目頁面")
        print("2. 點擊 'Variables' 選項卡")
        print("3. 添加上述缺少的環境變量")
        print("4. 重新部署項目")
    else:
        print("✅ 所有必需的環境變量都已設置!")
        
        # 額外檢查
        print("\n🔍 額外檢查:")
        
        # 檢查 TRON 地址格式
        usdt_addr = os.getenv('USDT_ADDRESS')
        if usdt_addr:
            if usdt_addr.startswith('T') and len(usdt_addr) == 34:
                print("✅ TRON 地址格式正確")
            else:
                print("❌ TRON 地址格式錯誤 (應該以T開頭，長度34字符)")
        
        # 檢查測試模式
        test_mode = os.getenv('TEST_MODE', '').lower()
        if test_mode == 'true':
            print("✅ 測試模式已啟用 (使用 TRX 支付)")
        else:
            print("ℹ️ 生產模式 (使用 USDT 支付)")
        
        # 檢查管理員ID
        admin_ids = os.getenv('ADMIN_IDS', '')
        if admin_ids:
            try:
                ids = [int(id.strip()) for id in admin_ids.split(',') if id.strip().isdigit()]
                print(f"✅ 找到 {len(ids)} 個管理員ID")
            except:
                print("❌ 管理員ID格式錯誤")

def check_trongrid_connection():
    """檢查 TronGrid 連接 (如果有 requests 模塊)"""
    try:
        import requests
        
        api_key = os.getenv('TRONGRID_API_KEY')
        if not api_key:
            print("⚠️ 跳過 TronGrid 連接測試 (API 密鑰未設置)")
            return
        
        print("\n🌐 測試 TronGrid API 連接...")
        
        headers = {
            'Content-Type': 'application/json',
            'TRON-PRO-API-KEY': api_key
        }
        
        url = "https://api.trongrid.io/wallet/getnowblock"
        
        try:
            response = requests.post(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                block_num = data.get('block_header', {}).get('raw_data', {}).get('number', 0)
                print(f"✅ TronGrid API 連接成功!")
                print(f"📊 當前區塊: {block_num}")
            else:
                print(f"❌ TronGrid API 連接失敗: HTTP {response.status_code}")
                print(f"   響應: {response.text[:200]}")
        except requests.exceptions.Timeout:
            print("⏰ TronGrid API 連接超時")
        except Exception as e:
            print(f"❌ TronGrid API 連接錯誤: {e}")
            
    except ImportError:
        print("⚠️ 跳過 TronGrid 連接測試 (requests 模塊未安裝)")

if __name__ == "__main__":
    check_railway_env()
    check_trongrid_connection()
    
    print("\n" + "="*50)
    print("🏁 檢查完成!")
    print("如果所有配置都正確，請重啟機器人服務")