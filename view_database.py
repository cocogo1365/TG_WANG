#!/usr/bin/env python3
"""
資料庫查看工具
查看已發出的訂單和激活碼
"""

import json
import os
from datetime import datetime
from pathlib import Path

def load_database():
    """載入資料庫"""
    try:
        db_path = Path(__file__).parent / "bot_database.json"
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 載入資料庫失敗: {e}")
        return None

def format_datetime(dt_str):
    """格式化時間"""
    if not dt_str:
        return "未設置"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

def view_orders(data):
    """查看訂單"""
    print("📋 已發出的訂單")
    print("=" * 80)
    
    orders = data.get("orders", {})
    if not orders:
        print("❌ 沒有找到任何訂單")
        return
    
    for order_id, order in orders.items():
        print(f"🆔 訂單ID: {order_id}")
        print(f"👤 用戶ID: {order['user_id']}")
        print(f"📦 方案類型: {order['plan_type']}")
        print(f"💰 金額: {order['amount']} {order['currency']}")
        print(f"📊 狀態: {order['status']}")
        if 'tx_hash' in order:
            print(f"🔗 交易Hash: {order['tx_hash']}")
        print(f"⏰ 創建時間: {format_datetime(order['created_at'])}")
        print(f"🔄 更新時間: {format_datetime(order['updated_at'])}")
        print(f"⌛ 過期時間: {format_datetime(order['expires_at'])}")
        print("-" * 80)

def view_activation_codes(data):
    """查看激活碼"""
    print("\n🔑 已發出的激活碼")
    print("=" * 80)
    
    codes = data.get("activation_codes", {})
    if not codes:
        print("❌ 沒有找到任何激活碼")
        return
    
    # 按創建時間排序
    sorted_codes = sorted(codes.items(), 
                         key=lambda x: x[1].get('created_at', ''), 
                         reverse=True)
    
    for code, info in sorted_codes:
        status = "✅ 已使用" if info.get('used') else "⭕ 未使用"
        
        print(f"🔑 激活碼: {code}")
        print(f"📦 方案類型: {info['plan_type']}")
        print(f"👤 用戶ID: {info['user_id']}")
        print(f"📋 訂單ID: {info.get('order_id', '無')}")
        print(f"📅 有效天數: {info['days']} 天")
        print(f"📊 使用狀態: {status}")
        
        if info.get('used'):
            print(f"⏰ 使用時間: {format_datetime(info.get('used_at'))}")
            print(f"💻 使用設備: {info.get('used_by_device', '未記錄')}")
        
        print(f"⏰ 創建時間: {format_datetime(info['created_at'])}")
        print(f"⌛ 過期時間: {format_datetime(info['expires_at'])}")
        
        if 'tx_hash' in info:
            print(f"🔗 交易Hash: {info['tx_hash']}")
        
        print("-" * 80)

def view_trial_users(data):
    """查看試用用戶"""
    print("\n👥 試用用戶列表")
    print("=" * 80)
    
    trial_users = data.get("trial_users", [])
    if not trial_users:
        print("❌ 沒有試用用戶")
        return
    
    for i, user_id in enumerate(trial_users, 1):
        print(f"{i}. 用戶ID: {user_id}")

def view_statistics(data):
    """查看統計信息"""
    print("\n📊 系統統計")
    print("=" * 80)
    
    stats = data.get("statistics", {})
    print(f"💰 總收入: {stats.get('total_revenue', 0)} TRX")
    print(f"📋 創建訂單數: {stats.get('orders_created', 0)}")
    print(f"🔑 生成激活碼數: {stats.get('activations_generated', 0)}")

def view_by_user(data, user_id):
    """查看特定用戶的記錄"""
    print(f"\n👤 用戶 {user_id} 的記錄")
    print("=" * 80)
    
    # 查看用戶的訂單
    user_orders = []
    for order_id, order in data.get("orders", {}).items():
        if order['user_id'] == user_id:
            user_orders.append((order_id, order))
    
    if user_orders:
        print("📋 用戶訂單:")
        for order_id, order in user_orders:
            print(f"  🆔 {order_id} - {order['plan_type']} - {order['status']} - {order['amount']} TRX")
    
    # 查看用戶的激活碼
    user_codes = []
    for code, info in data.get("activation_codes", {}).items():
        if info['user_id'] == user_id:
            user_codes.append((code, info))
    
    if user_codes:
        print("🔑 用戶激活碼:")
        for code, info in user_codes:
            status = "已使用" if info.get('used') else "未使用"
            print(f"  🔑 {code} - {info['plan_type']} - {status}")

def search_by_activation_code(data, activation_code):
    """根據激活碼搜索"""
    print(f"\n🔍 搜索激活碼: {activation_code}")
    print("=" * 80)
    
    codes = data.get("activation_codes", {})
    if activation_code in codes:
        info = codes[activation_code]
        print(f"✅ 找到激活碼!")
        print(f"📦 方案類型: {info['plan_type']}")
        print(f"👤 用戶ID: {info['user_id']}")
        print(f"📋 訂單ID: {info.get('order_id', '無')}")
        print(f"📅 有效天數: {info['days']} 天")
        print(f"📊 使用狀態: {'已使用' if info.get('used') else '未使用'}")
        
        if info.get('used'):
            print(f"⏰ 使用時間: {format_datetime(info.get('used_at'))}")
            print(f"💻 使用設備: {info.get('used_by_device', '未記錄')}")
        
        print(f"⏰ 創建時間: {format_datetime(info['created_at'])}")
        print(f"⌛ 過期時間: {format_datetime(info['expires_at'])}")
    else:
        print("❌ 未找到該激活碼")

def main():
    """主程序"""
    print("🚀 TG旺機器人 - 資料庫查看工具")
    print("=" * 80)
    
    # 載入資料庫
    data = load_database()
    if not data:
        return
    
    while True:
        print("\n📋 選擇查看選項:")
        print("1. 查看所有訂單")
        print("2. 查看所有激活碼")
        print("3. 查看試用用戶")
        print("4. 查看統計信息")
        print("5. 查看特定用戶記錄")
        print("6. 搜索激活碼")
        print("7. 查看所有信息")
        print("0. 退出")
        
        choice = input("\n請輸入選項 (0-7): ").strip()
        
        if choice == '1':
            view_orders(data)
        elif choice == '2':
            view_activation_codes(data)
        elif choice == '3':
            view_trial_users(data)
        elif choice == '4':
            view_statistics(data)
        elif choice == '5':
            try:
                user_id = int(input("請輸入用戶ID: "))
                view_by_user(data, user_id)
            except ValueError:
                print("❌ 請輸入有效的用戶ID")
        elif choice == '6':
            activation_code = input("請輸入激活碼: ").strip()
            search_by_activation_code(data, activation_code)
        elif choice == '7':
            view_orders(data)
            view_activation_codes(data)
            view_trial_users(data)
            view_statistics(data)
        elif choice == '0':
            print("👋 再見!")
            break
        else:
            print("❌ 無效選項，請重新選擇")

if __name__ == "__main__":
    main()