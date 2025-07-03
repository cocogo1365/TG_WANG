#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查特定付款狀態
"""

import os
import json
from datetime import datetime, timedelta

def check_current_setup():
    """檢查當前配置"""
    print("🔧 當前配置檢查:")
    
    usdt_address = os.getenv('USDT_ADDRESS')
    test_mode = os.getenv('TEST_MODE')
    api_key = os.getenv('TRONGRID_API_KEY')
    
    print(f"📧 監控地址: {usdt_address}")
    print(f"🧪 測試模式: {test_mode}")
    print(f"🔑 API 密鑰: {'已設置' if api_key else '未設置'}")
    
    if usdt_address == 'TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP':
        print("✅ 地址設置正確")
    else:
        print(f"❌ 地址不匹配！當前: {usdt_address}")
    
    return usdt_address, test_mode, api_key

def check_database_orders():
    """檢查數據庫中的訂單"""
    print("\n📋 檢查數據庫訂單:")
    
    db_file = 'bot_database.json'
    if not os.path.exists(db_file):
        print("❌ 數據庫文件不存在 - 機器人可能沒有運行")
        return []
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orders = data.get('orders', {})
        transactions = data.get('transactions', {})
        
        print(f"📊 總訂單數: {len(orders)}")
        print(f"💰 總交易數: {len(transactions)}")
        
        # 查找最近的訂單
        recent_orders = []
        now = datetime.now()
        
        for order_id, order in orders.items():
            try:
                created_at = datetime.fromisoformat(order['created_at'])
                age_hours = (now - created_at).total_seconds() / 3600
                
                if age_hours < 2:  # 最近2小時
                    recent_orders.append({
                        'order_id': order_id,
                        'amount': order['amount'],
                        'status': order['status'],
                        'created_at': created_at,
                        'age_minutes': (now - created_at).total_seconds() / 60,
                        'currency': order.get('currency', 'USDT')
                    })
            except:
                continue
        
        # 按時間排序
        recent_orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        print(f"\n📋 最近2小時的訂單 ({len(recent_orders)} 個):")
        for order in recent_orders:
            status_icon = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "expired": "⏰"}.get(order['status'], "❓")
            print(f"  {status_icon} {order['order_id']}")
            print(f"     金額: {order['amount']} {order['currency']}")
            print(f"     狀態: {order['status']}")
            print(f"     創建: {order['created_at'].strftime('%H:%M:%S')}")
            print(f"     經過: {order['age_minutes']:.1f} 分鐘")
            
            if order['age_minutes'] > 30:
                print(f"     ⚠️ 已超過30分鐘限制")
            print()
        
        return recent_orders
        
    except Exception as e:
        print(f"❌ 讀取數據庫失敗: {e}")
        return []

def check_transactions():
    """檢查交易記錄"""
    print("💰 檢查交易記錄:")
    
    db_file = 'bot_database.json'
    if not os.path.exists(db_file):
        return
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transactions = data.get('transactions', {})
        
        if not transactions:
            print("  📝 沒有交易記錄")
            return
        
        # 按時間排序
        tx_list = []
        for tx_id, tx in transactions.items():
            try:
                tx_time = datetime.fromisoformat(tx['timestamp'])
                tx_list.append({
                    'tx_id': tx_id,
                    'amount': tx['amount'],
                    'currency': tx.get('currency', 'USDT'),
                    'timestamp': tx_time,
                    'from_address': tx.get('from_address', '未知')
                })
            except:
                continue
        
        tx_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        print(f"  📊 找到 {len(tx_list)} 個交易記錄")
        
        for tx in tx_list[:5]:  # 顯示最近5個
            print(f"    💸 {tx['amount']} {tx['currency']} - {tx['timestamp'].strftime('%H:%M:%S')}")
            print(f"       發送方: {tx['from_address'][:16]}...")
            print(f"       交易: {tx['tx_id'][:16]}...")
            print()
    
    except Exception as e:
        print(f"❌ 讀取交易記錄失敗: {e}")

def provide_recommendations(orders):
    """提供建議"""
    print("🔧 診斷建議:")
    
    if not orders:
        print("1. ❌ 沒有找到最近的訂單")
        print("   - 確認您已經通過機器人創建了訂單")
        print("   - 檢查機器人是否正在運行")
        print("   - 嘗試重新創建測試訂單")
        return
    
    pending_orders = [o for o in orders if o['status'] == 'pending']
    
    if not pending_orders:
        print("1. ℹ️ 沒有待付款訂單")
        print("   - 所有訂單都已處理或取消")
        print("   - 可能需要創建新的測試訂單")
        return
    
    print("1. ⏳ 找到待付款訂單:")
    for order in pending_orders:
        print(f"   - 訂單 {order['order_id']}: {order['amount']} {order['currency']}")
        
        if order['age_minutes'] > 30:
            print(f"     ❌ 已過期 ({order['age_minutes']:.1f} 分鐘)")
            print(f"     建議: 創建新訂單")
        else:
            print(f"     ✅ 仍在有效期內 ({30 - order['age_minutes']:.1f} 分鐘剩餘)")
            print(f"     建議: 確認已發送 {order['amount']} TRX 到 TGEhjpGrYT2mtST2vHxTd5dTxfh21UzkRP")
    
    print("\n2. 📡 檢查機器人監控:")
    print("   - 在 Railway.com Logs 中查找 '開始監控 TRX 交易'")
    print("   - 確認 API 密鑰設置正確")
    print("   - 檢查是否有 API 錯誤信息")
    
    print("\n3. 🔍 手動檢查:")
    print("   - 運行: python3 manual_test.py")
    print("   - 檢查 TronScan 上的交易記錄")
    print("   - 確認付款金額完全匹配")

def main():
    """主函數"""
    print("🔍 付款狀態診斷工具")
    print("="*50)
    
    # 檢查配置
    usdt_address, test_mode, api_key = check_current_setup()
    
    print("="*50)
    
    # 檢查訂單
    orders = check_database_orders()
    
    print("="*50)
    
    # 檢查交易
    check_transactions()
    
    print("="*50)
    
    # 提供建議
    provide_recommendations(orders)

if __name__ == "__main__":
    main()