#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的系統診斷工具
"""

import os
import json
import urllib.request
import urllib.parse
import sys
from datetime import datetime

def check_environment():
    """檢查環境變量"""
    print("🔧 檢查環境變量...")
    
    required_vars = {
        'BOT_TOKEN': '機器人Token',
        'USDT_ADDRESS': 'TRON錢包地址', 
        'USDT_CONTRACT': 'USDT合約地址',
        'TRONGRID_API_KEY': 'TronScan API密鑰',
        'TEST_MODE': '測試模式',
        'ADMIN_IDS': '管理員ID'
    }
    
    missing = []
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            if var in ['BOT_TOKEN', 'TRONGRID_API_KEY']:
                display = f"{value[:8]}..."
            else:
                display = value
            print(f"  ✅ {var}: {display}")
        else:
            print(f"  ❌ {var}: 未設置 ({desc})")
            missing.append(var)
    
    return len(missing) == 0

def test_api_connection():
    """測試 API 連接"""
    print("\n🌐 測試 TronScan API 連接...")
    
    api_key = os.getenv('TRONGRID_API_KEY')
    if not api_key:
        print("❌ API 密鑰未設置")
        return False
    
    # 測試區塊查詢
    try:
        url = "https://apilist.tronscanapi.com/api/block"
        headers = {'TRON-PRO-API-KEY': api_key}
        
        req = urllib.request.Request(url, headers=headers, method='GET')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            data = json.loads(response.read().decode('utf-8'))
            
            print(f"  📡 API 請求狀態: {status}")
            
            if status == 200:
                print("  ✅ API 連接成功!")
                
                # 解析區塊數據
                if isinstance(data, list) and len(data) > 0:
                    block_num = data[0].get('number', 0)
                elif isinstance(data, dict):
                    block_num = data.get('number', 0)
                else:
                    block_num = 0
                
                print(f"  📊 當前區塊: {block_num}")
                return True
            else:
                print(f"  ❌ API 請求失敗: {status}")
                return False
                
    except Exception as e:
        print(f"  ❌ API 請求異常: {e}")
        return False

def test_bot_components():
    """測試機器人組件"""
    print("\n🤖 測試機器人組件...")
    
    try:
        # 測試配置模塊
        sys.path.append('.')
        from config import Config
        config = Config()
        print("  ✅ Config 模塊正常")
        
        # 測試數據庫模塊
        from database import Database
        db = Database()
        print("  ✅ Database 模塊正常")
        
        # 測試 TronMonitor 模塊
        from tron_monitor import TronMonitor
        monitor = TronMonitor()
        print(f"  ✅ TronMonitor 模塊正常 (測試模式: {monitor.test_mode})")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ 模塊導入失敗: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 組件初始化失敗: {e}")
        return False

def check_database():
    """檢查數據庫狀態"""
    print("\n📊 檢查數據庫狀態...")
    
    db_file = 'bot_database.json'
    if not os.path.exists(db_file):
        print("  ⚠️ 數據庫文件不存在 - 機器人可能沒有運行過")
        return False
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orders = data.get('orders', {})
        transactions = data.get('transactions', {})
        
        print(f"  📋 總訂單數: {len(orders)}")
        print(f"  💰 總交易數: {len(transactions)}")
        
        # 檢查最近的活動
        if orders:
            latest_order = max(orders.values(), key=lambda x: x.get('created_at', ''))
            print(f"  🕐 最新訂單: {latest_order.get('created_at', '未知')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 讀取數據庫失敗: {e}")
        return False

def check_railway_logs():
    """提示檢查 Railway 日誌"""
    print("\n📋 Railway.com 日誌檢查指南...")
    print("  請在 Railway.com 中檢查以下日誌信息:")
    print("  1. 機器人啟動日誌:")
    print("     ✅ 機器人初始化完成，智能監控待命中...")
    print("     🧪 測試模式: 開啟")
    print("  2. API 錯誤日誌:")
    print("     ❌ 無法連接到 TronGrid API")
    print("     ❌ API 密鑰: 未設置")
    print("  3. 用戶互動日誌:")
    print("     🔍 開始監控 TRX 交易... (創建訂單後)")

def provide_action_plan():
    """提供行動計劃"""
    print("\n🎯 診斷結果和行動計劃:")
    
    print("\n如果所有環境變量和 API 都正常:")
    print("  1. 📱 測試機器人響應:")
    print("     - 向機器人發送 /start")
    print("     - 檢查是否收到回應")
    
    print("\n  2. 🛒 創建測試訂單:")
    print("     - 點擊 '🧪 1 TRX 測試購買'")
    print("     - 選擇測試方案")
    print("     - 創建訂單 ← 這一步才會觸發 API 調用")
    
    print("\n  3. 📊 檢查監控啟動:")
    print("     - 在 Railway.com Logs 中查找:")
    print("     - '🔍 開始監控 TRX 交易'")
    print("     - '訂單 TGxxxxxxxx 加入監控列表'")
    
    print("\n  4. 🔍 檢查 API 調用:")
    print("     - 回到 TronScan API Keys 頁面")
    print("     - 查看 TG-WANG 的 Calls 統計")
    print("     - 應該每分鐘增加 1-2 次調用")

def main():
    """主診斷函數"""
    print("🚀 TG-WANG 系統完整診斷")
    print("=" * 60)
    print(f"診斷時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 逐步診斷
    env_ok = check_environment()
    print("=" * 60)
    
    api_ok = test_api_connection()
    print("=" * 60)
    
    components_ok = test_bot_components()
    print("=" * 60)
    
    db_ok = check_database()
    print("=" * 60)
    
    check_railway_logs()
    print("=" * 60)
    
    # 總結
    print("🏁 診斷總結:")
    print(f"  環境變量: {'✅' if env_ok else '❌'}")
    print(f"  API 連接: {'✅' if api_ok else '❌'}")
    print(f"  機器人組件: {'✅' if components_ok else '❌'}")
    print(f"  數據庫: {'✅' if db_ok else '⚠️'}")
    
    if env_ok and api_ok and components_ok:
        print("\n🎉 基礎配置全部正確!")
        print("問題可能是：機器人沒有創建訂單，因此沒有觸發監控")
    else:
        print("\n🔧 發現配置問題，請先修復上述錯誤")
    
    print("=" * 60)
    provide_action_plan()

if __name__ == "__main__":
    main()