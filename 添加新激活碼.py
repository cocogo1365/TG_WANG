#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加新購買的激活碼到數據庫
"""

import json
from datetime import datetime, timedelta

def add_new_activation_code():
    """添加新激活碼"""
    
    # 您的新激活碼信息
    activation_code = "YM454P8E7DD57RNM"
    order_id = "TG634241FI5Q"
    plan_type = "weekly"  # 測試方案是週卡
    days = 7
    user_id = 7537903238
    tx_hash = "03cc6392b466a2742aa923a22ae4d0aaf057a16c80e420be547ff5808bf95022"
    
    print(f"🔧 正在添加激活碼 {activation_code} 到數據庫...")
    
    try:
        # 讀取數據庫
        db_file = 'bot_database.json'
        with open(db_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 創建激活碼數據
        expires_at = datetime.now() + timedelta(days=days)
        code_data = {
            "activation_code": activation_code,
            "plan_type": plan_type,
            "user_id": user_id,
            "order_id": order_id,
            "days": days,
            "created_at": "2025-07-04T13:06:04",
            "expires_at": expires_at.isoformat(),
            "used": False,
            "used_at": None,
            "used_by_device": None,
            "tx_hash": tx_hash
        }
        
        # 添加到數據庫
        data['activation_codes'][activation_code] = code_data
        
        # 添加訂單信息
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "plan_type": plan_type,
            "amount": 1.04,
            "currency": "TRX",
            "status": "paid",
            "tx_hash": tx_hash,
            "created_at": "2025-07-04T13:05:00",
            "updated_at": "2025-07-04T13:06:04",
            "expires_at": expires_at.isoformat()
        }
        
        data['orders'][order_id] = order_data
        
        # 更新統計
        if 'orders_created' in data['statistics']:
            data['statistics']['orders_created'] += 1
        if 'activations_generated' in data['statistics']:
            data['statistics']['activations_generated'] += 1
        if 'total_revenue' in data['statistics']:
            data['statistics']['total_revenue'] += 1.04
        
        # 保存數據庫
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 激活碼 {activation_code} 已成功添加到數據庫")
        print(f"📋 詳細信息:")
        print(f"  訂單號: {order_id}")
        print(f"  方案類型: {plan_type} (7天)")
        print(f"  到期時間: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 添加激活碼失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_new_activation_code()
    if success:
        print("\n🎉 激活碼同步成功!")
        print("現在您可以在軟件中使用激活碼 YM454P8E7DD57RNM 了")
        
        # 提示推送到Railway
        print("\n📤 請推送更新到Railway:")
        print("git add bot_database.json")
        print('git commit -m "Add new activation code YM454P8E7DD57RNM"')
        print("git push origin main")
    else:
        print("\n❌ 激活碼同步失敗")