#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化付款診斷工具
"""

import os
import json
from datetime import datetime, timedelta

def check_database():
    """檢查數據庫狀態"""
    print("🔍 檢查數據庫狀態...")
    
    # 檢查數據庫文件
    db_file = 'bot_database.json'
    if not os.path.exists(db_file):
        print(f"❌ 數據庫文件不存在: {db_file}")
        return
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orders = data.get('orders', {})
        transactions = data.get('transactions', {})
        
        print(f"✅ 數據庫文件存在: {db_file}")
        print(f"📊 總訂單數: {len(orders)}")
        print(f"💰 總交易數: {len(transactions)}")
        
        # 檢查最近的訂單
        now = datetime.now()
        recent_orders = []
        
        for order_id, order in orders.items():
            try:
                created_at = datetime.fromisoformat(order['created_at'])
                if now - created_at < timedelta(hours=2):  # 最近2小時
                    recent_orders.append(order)
            except:
                continue
        
        print(f"\n📋 最近2小時的訂單 ({len(recent_orders)} 個):")
        for order in recent_orders[-5:]:  # 顯示最近5個
            status_icon = {"pending": "⏳", "paid": "✅", "cancelled": "❌", "expired": "⏰"}.get(order['status'], "❓")
            currency = order.get('currency', 'USDT')
            print(f"  {status_icon} {order['order_id']}: {order['amount']} {currency} - {order['status']}")
            print(f"    創建時間: {order['created_at']}")
            print(f"    用戶ID: {order['user_id']}")
            
            # 如果是待付款狀態，檢查是否應該過期
            if order['status'] == 'pending':
                created_at = datetime.fromisoformat(order['created_at'])
                age_minutes = (now - created_at).total_seconds() / 60
                print(f"    等待時間: {age_minutes:.1f} 分鐘 {'(應該自動取消)' if age_minutes > 30 else '(仍在有效期內)'}")
            print()
        
        # 檢查最近的交易
        print(f"\n💰 最近的交易記錄 ({len(transactions)} 個):")
        recent_transactions = []
        for tx_id, tx in transactions.items():
            try:
                tx_time = datetime.fromisoformat(tx['timestamp'])
                if now - tx_time < timedelta(hours=2):
                    recent_transactions.append(tx)
            except:
                continue
                
        for tx in recent_transactions[-3:]:  # 顯示最近3個
            currency = tx.get('currency', 'USDT')
            print(f"  💸 {tx['amount']} {currency} - {tx['timestamp']}")
            print(f"    交易哈希: {tx['tx_hash']}")
            print(f"    發送方: {tx.get('from_address', '未知')}")
            print()
        
    except Exception as e:
        print(f"❌ 讀取數據庫失敗: {e}")

def check_environment():
    """檢查環境配置"""
    print("🔧 檢查環境配置...")
    
    env_vars = [
        'BOT_TOKEN',
        'USDT_ADDRESS', 
        'TRONGRID_API_KEY',
        'TEST_MODE',
        'ADMIN_IDS'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # 隱藏敏感信息
            if var in ['BOT_TOKEN', 'TRONGRID_API_KEY']:
                display_value = f"{value[:10]}..." if len(value) > 10 else "已設置"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: 未設置")
    
    print()

def main():
    """主函數"""
    print("🚀 TG營銷系統付款診斷工具")
    print("="*50)
    
    check_environment()
    print("="*50)
    check_database()
    
    print("="*50)
    print("🔍 診斷建議:")
    print("1. 確保 TRONGRID_API_KEY 已正確設置")
    print("2. 確保機器人正在運行 (python3 main.py)")
    print("3. 檢查訂單是否在30分鐘有效期內")
    print("4. 確認付款金額與訂單金額完全匹配")
    print("5. 查看機器人日誌文件 (bot.log) 了解詳細錯誤")

if __name__ == "__main__":
    main()