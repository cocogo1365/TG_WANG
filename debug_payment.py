#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
付款診斷工具 - 檢查 TRX 交易監控是否正常工作
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from config import Config
from database import Database
from tron_monitor import TronMonitor

async def debug_payment_monitoring():
    """診斷付款監控系統"""
    print("🔍 開始診斷付款監控系統...")
    
    # 設置測試模式
    os.environ['TEST_MODE'] = 'true'
    
    try:
        # 初始化組件
        config = Config()
        db = Database()
        monitor = TronMonitor()
        
        print(f"✅ 配置加載成功")
        print(f"📧 收款地址: {config.USDT_ADDRESS}")
        print(f"🔑 API密鑰: {'已設置' if config.TRONGRID_API_KEY else '未設置'}")
        print(f"🧪 測試模式: {monitor.test_mode}")
        print(f"⏰ 監控間隔: {config.MONITORING_INTERVAL}秒")
        
        print("\n" + "="*50)
        
        # 檢查最近的訂單
        print("📋 檢查最近的訂單...")
        if hasattr(db.data, 'orders'):
            orders = db.data['orders']
        else:
            orders = db.data.get('orders', {})
            
        recent_orders = []
        now = datetime.now()
        for order_id, order in orders.items():
            created_at = datetime.fromisoformat(order['created_at'])
            if now - created_at < timedelta(hours=1):
                recent_orders.append(order)
                
        print(f"📊 找到 {len(recent_orders)} 個最近1小時的訂單")
        
        for order in recent_orders[-3:]:  # 顯示最近3個
            print(f"  • 訂單 {order['order_id']}: {order['amount']} {order.get('currency', 'USDT')} - {order['status']}")
        
        print("\n" + "="*50)
        
        # 測試 TronGrid API 連接
        print("🌐 測試 TronGrid API 連接...")
        try:
            current_block = await monitor.get_latest_block_number()
            print(f"✅ API 連接成功，當前區塊: {current_block}")
        except Exception as e:
            print(f"❌ API 連接失敗: {e}")
            return
        
        print("\n" + "="*50)
        
        # 檢查最近的 TRX 交易
        print("💰 檢查最近的 TRX 交易...")
        try:
            transactions = await monitor.get_trx_transactions(10)
            print(f"📊 找到 {len(transactions)} 個 TRX 交易")
            
            for tx in transactions[:3]:  # 顯示最近3個
                amount = float(tx.get('value', 0)) / 1_000_000  # 轉換為 TRX
                timestamp = tx.get('block_timestamp', 0)
                tx_time = datetime.fromtimestamp(timestamp / 1000) if timestamp else None
                print(f"  • {amount:.3f} TRX - {tx_time.strftime('%H:%M:%S') if tx_time else '未知時間'}")
                
        except Exception as e:
            print(f"❌ 獲取 TRX 交易失敗: {e}")
        
        print("\n" + "="*50)
        
        # 手動驗證付款
        print("🔍 手動驗證付款...")
        
        # 獲取待付款訂單的金額
        pending_orders = [o for o in recent_orders if o['status'] == 'pending']
        if pending_orders:
            print(f"📋 找到 {len(pending_orders)} 個待付款訂單")
            
            for order in pending_orders:
                amount = order['amount']
                print(f"\n🔍 檢查訂單 {order['order_id']} 的付款 ({amount} TRX)...")
                
                try:
                    payment = await monitor.verify_payment(amount, max_age_minutes=60)
                    if payment:
                        print(f"✅ 找到匹配的付款!")
                        print(f"  • 交易哈希: {payment['tx_hash']}")
                        print(f"  • 金額: {payment['amount']} {payment.get('currency', 'TRX')}")
                        print(f"  • 發送方: {payment['from_address']}")
                    else:
                        print(f"❌ 未找到匹配的付款")
                        
                except Exception as e:
                    print(f"❌ 驗證付款失敗: {e}")
        else:
            print("📋 沒有待付款訂單")
        
        print("\n" + "="*50)
        print("🏁 診斷完成!")
        
    except Exception as e:
        print(f"❌ 診斷過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_payment_monitoring())