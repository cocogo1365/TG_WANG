#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫管理模塊 - 使用 JSON 文件作為簡單數據庫
"""

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class Database:
    """簡單的 JSON 數據庫"""
    
    def __init__(self, db_file: str = 'bot_database.json'):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """加載數據"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # 初始化數據結構
        return {
            'users': {},
            'orders': {},
            'activation_codes': {},
            'trial_users': set(),
            'transactions': {},
            'statistics': {
                'total_revenue': 0.0,
                'orders_created': 0,
                'activations_generated': 0
            }
        }
    
    def _save_data(self):
        """保存數據"""
        try:
            # 轉換 set 為 list 以便 JSON 序列化
            data_to_save = self.data.copy()
            data_to_save['trial_users'] = list(self.data['trial_users'])
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"❌ 保存數據失敗: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """添加用戶"""
        with self.lock:
            if str(user_id) not in self.data['users']:
                self.data['users'][str(user_id)] = {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'created_at': datetime.now().isoformat(),
                    'last_active': datetime.now().isoformat()
                }
            else:
                # 更新最後活躍時間
                self.data['users'][str(user_id)]['last_active'] = datetime.now().isoformat()
            
            self._save_data()
    
    def has_used_trial(self, user_id: int) -> bool:
        """檢查用戶是否已使用過試用"""
        return user_id in self.data['trial_users']
    
    def mark_trial_used(self, user_id: int):
        """標記用戶已使用試用"""
        with self.lock:
            self.data['trial_users'].add(user_id)
            self._save_data()
    
    def create_order(self, order_data: Dict):
        """創建訂單"""
        with self.lock:
            order_id = order_data['order_id']
            self.data['orders'][order_id] = order_data
            self.data['statistics']['orders_created'] += 1
            self._save_data()
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """獲取訂單"""
        return self.data['orders'].get(order_id)
    
    def update_order_status(self, order_id: str, status: str, tx_hash: str = None):
        """更新訂單狀態"""
        with self.lock:
            if order_id in self.data['orders']:
                self.data['orders'][order_id]['status'] = status
                self.data['orders'][order_id]['updated_at'] = datetime.now().isoformat()
                
                if tx_hash:
                    self.data['orders'][order_id]['tx_hash'] = tx_hash
                
                if status == 'paid':
                    amount = self.data['orders'][order_id]['amount']
                    self.data['statistics']['total_revenue'] += amount
                
                self._save_data()
    
    def find_order_by_amount(self, amount: float) -> Optional[Dict]:
        """根據金額查找待付款訂單"""
        for order in self.data['orders'].values():
            if (order['status'] == 'pending' and 
                abs(order['amount'] - amount) < 0.01):  # 允許小數點誤差
                return order
        return None
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        """獲取用戶的所有訂單"""
        user_orders = []
        for order in self.data['orders'].values():
            if order['user_id'] == user_id:
                user_orders.append(order)
        
        # 按創建時間排序
        user_orders.sort(key=lambda x: x['created_at'], reverse=True)
        return user_orders
    
    def save_activation_code(self, code_data: Dict):
        """保存激活碼"""
        with self.lock:
            activation_code = code_data['activation_code']
            self.data['activation_codes'][activation_code] = code_data
            self.data['statistics']['activations_generated'] += 1
            self._save_data()
    
    def get_activation_code(self, activation_code: str) -> Optional[Dict]:
        """獲取激活碼信息"""
        return self.data['activation_codes'].get(activation_code)
    
    def get_activation_code_by_order(self, order_id: str) -> Optional[str]:
        """根據訂單ID獲取激活碼"""
        for code, data in self.data['activation_codes'].items():
            if data.get('order_id') == order_id:
                return code
        return None
    
    def save_transaction(self, tx_hash: str, transaction_data: Dict):
        """保存交易記錄"""
        with self.lock:
            self.data['transactions'][tx_hash] = transaction_data
            self._save_data()
    
    def transaction_exists(self, tx_hash: str) -> bool:
        """檢查交易是否已存在"""
        return tx_hash in self.data['transactions']
    
    def cleanup_expired_orders(self):
        """清理過期訂單"""
        with self.lock:
            current_time = datetime.now()
            expired_orders = []
            
            for order_id, order in self.data['orders'].items():
                if order['status'] == 'pending':
                    expires_at = datetime.fromisoformat(order['expires_at'])
                    if current_time > expires_at:
                        expired_orders.append(order_id)
            
            for order_id in expired_orders:
                self.data['orders'][order_id]['status'] = 'expired'
            
            if expired_orders:
                self._save_data()
            
            return len(expired_orders)
    
    def get_statistics(self) -> Dict:
        """獲取統計數據"""
        stats = self.data['statistics'].copy()
        
        # 計算額外統計
        stats['total_users'] = len(self.data['users'])
        stats['total_orders'] = len(self.data['orders'])
        stats['trial_users'] = len(self.data['trial_users'])
        
        # 按狀態統計訂單
        status_counts = {}
        for order in self.data['orders'].values():
            status = order['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats['pending_orders'] = status_counts.get('pending', 0)
        stats['completed_orders'] = status_counts.get('paid', 0)
        stats['expired_orders'] = status_counts.get('expired', 0)
        
        # 激活碼統計
        stats['total_activations'] = len(self.data['activation_codes'])
        stats['used_activations'] = sum(1 for code_data in self.data['activation_codes'].values() 
                                       if code_data.get('used', False))
        stats['trial_activations'] = sum(1 for code_data in self.data['activation_codes'].values() 
                                        if code_data.get('plan_type') == 'trial')
        
        # 今日收入
        today = datetime.now().date()
        today_revenue = 0.0
        for order in self.data['orders'].values():
            if order['status'] == 'paid':
                order_date = datetime.fromisoformat(order['created_at']).date()
                if order_date == today:
                    today_revenue += order['amount']
        
        stats['today_revenue'] = today_revenue
        
        return stats
    
    def get_recent_orders_by_amount(self, amount: float, hours: int = 1) -> List[Dict]:
        """獲取指定時間內相同金額的訂單"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        matching_orders = []
        
        for order in self.data['orders'].values():
            order_time = datetime.fromisoformat(order['created_at'])
            if (order_time > cutoff_time and 
                abs(order['amount'] - amount) < 0.001):  # 允許極小誤差
                matching_orders.append(order)
        
        return matching_orders
    
    def get_recent_orders(self, days: int = 7) -> List[Dict]:
        """獲取最近的訂單"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_orders = []
        
        for order in self.data['orders'].values():
            order_date = datetime.fromisoformat(order['created_at'])
            if order_date > cutoff_date:
                recent_orders.append(order)
        
        recent_orders.sort(key=lambda x: x['created_at'], reverse=True)
        return recent_orders
    
    def export_data(self) -> Dict:
        """導出所有數據"""
        return self.data.copy()
    
    def backup_database(self, backup_file: str = None):
        """備份數據庫"""
        if not backup_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_{timestamp}.json"
        
        try:
            data_to_backup = self.data.copy()
            data_to_backup['trial_users'] = list(self.data['trial_users'])
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_backup, f, ensure_ascii=False, indent=2)
            
            return backup_file
        except IOError as e:
            print(f"❌ 備份失敗: {e}")
            return None