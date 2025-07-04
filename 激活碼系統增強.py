#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活碼系統增強 - 商業化功能
"""

import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, List

class EnhancedActivationSystem:
    """增強版激活碼系統"""
    
    def __init__(self):
        # 定價方案
        self.pricing_plans = {
            'trial': {
                'name': '免費試用',
                'days': 2,
                'price': 0,
                'features': ['基礎功能', '限制100個操作/天']
            },
            'weekly': {
                'name': '週卡',
                'days': 7,
                'price': 5,
                'features': ['完整功能', '無限制操作', '基礎客服']
            },
            'monthly': {
                'name': '月卡',
                'days': 30,
                'price': 15,
                'features': ['完整功能', '無限制操作', '優先客服', '數據導出']
            },
            'quarterly': {
                'name': '季度卡',
                'days': 90,
                'price': 35,
                'features': ['完整功能', '無限制操作', 'VIP客服', '數據導出', 'API訪問']
            },
            'yearly': {
                'name': '年卡',
                'days': 365,
                'price': 99,
                'features': ['完整功能', '無限制操作', 'VIP客服', '數據導出', 'API訪問', '免費更新']
            },
            'lifetime': {
                'name': '終身版',
                'days': 36500,  # 100年
                'price': 199,
                'features': ['所有當前和未來功能', '最高優先級支持', '源碼授權']
            }
        }
        
        # 促銷代碼
        self.promo_codes = {
            'LAUNCH50': {'discount': 0.5, 'expires': '2025-12-31'},
            'FRIEND20': {'discount': 0.2, 'expires': '2025-12-31'},
            'VIP30': {'discount': 0.3, 'expires': '2025-12-31'}
        }
    
    def generate_secure_activation_code(self, plan_type: str, user_id: int, 
                                      order_id: str, secret_key: str = "your-secret-key") -> str:
        """生成安全的激活碼（包含簽名）"""
        # 基礎信息
        timestamp = int(datetime.now().timestamp())
        data = f"{plan_type}:{user_id}:{order_id}:{timestamp}"
        
        # 生成簽名
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).digest()
        
        # 編碼為激活碼
        code_data = f"{data}:{base64.b64encode(signature).decode()}"
        encoded = base64.b64encode(code_data.encode()).decode()
        
        # 格式化為用戶友好的格式 (去除特殊字符)
        clean_code = encoded.replace('+', '').replace('/', '').replace('=', '')
        
        # 分組顯示 XXXX-XXXX-XXXX-XXXX
        formatted_code = '-'.join([clean_code[i:i+4] for i in range(0, min(16, len(clean_code)), 4)])
        
        return formatted_code.upper()
    
    def calculate_price_with_promo(self, plan_type: str, promo_code: Optional[str] = None) -> Dict:
        """計算促銷後的價格"""
        if plan_type not in self.pricing_plans:
            return {'error': '無效的方案類型'}
        
        base_price = self.pricing_plans[plan_type]['price']
        discount = 0
        
        if promo_code and promo_code in self.promo_codes:
            promo = self.promo_codes[promo_code]
            # 檢查是否過期
            if datetime.now().strftime('%Y-%m-%d') <= promo['expires']:
                discount = base_price * promo['discount']
        
        final_price = base_price - discount
        
        return {
            'plan': plan_type,
            'base_price': base_price,
            'discount': discount,
            'final_price': final_price,
            'promo_code': promo_code if discount > 0 else None
        }
    
    def generate_batch_codes(self, plan_type: str, quantity: int, 
                           batch_id: str, user_id: int) -> List[str]:
        """批量生成激活碼（企業客戶）"""
        codes = []
        for i in range(quantity):
            order_id = f"{batch_id}_{i+1:04d}"
            code = self.generate_secure_activation_code(plan_type, user_id, order_id)
            codes.append(code)
        return codes
    
    def get_activation_statistics(self, db) -> Dict:
        """獲取激活碼統計數據"""
        stats = {
            'total_revenue': 0,
            'revenue_by_plan': {},
            'activation_by_plan': {},
            'daily_revenue': {},
            'conversion_rate': 0,
            'average_order_value': 0
        }
        
        # 統計每個方案的收入和激活數
        for plan_type, plan_info in self.pricing_plans.items():
            plan_revenue = 0
            plan_count = 0
            
            for code_data in db.data.get('activation_codes', {}).values():
                if code_data.get('plan_type') == plan_type and code_data.get('used'):
                    plan_revenue += plan_info['price']
                    plan_count += 1
            
            stats['revenue_by_plan'][plan_type] = plan_revenue
            stats['activation_by_plan'][plan_type] = plan_count
            stats['total_revenue'] += plan_revenue
        
        # 計算試用轉付費率
        trial_users = len(db.data.get('trial_users', []))
        paid_users = sum(count for plan, count in stats['activation_by_plan'].items() 
                        if plan != 'trial' and count > 0)
        
        if trial_users > 0:
            stats['conversion_rate'] = (paid_users / trial_users) * 100
        
        # 計算平均訂單價值
        total_orders = sum(stats['activation_by_plan'].values())
        if total_orders > 0:
            stats['average_order_value'] = stats['total_revenue'] / total_orders
        
        return stats
    
    def check_upgrade_eligibility(self, current_plan: str, target_plan: str, 
                                remaining_days: int) -> Dict:
        """檢查升級資格並計算升級價格"""
        current_price = self.pricing_plans.get(current_plan, {}).get('price', 0)
        target_price = self.pricing_plans.get(target_plan, {}).get('price', 0)
        
        if target_price <= current_price:
            return {'eligible': False, 'reason': '只能升級到更高級的方案'}
        
        # 計算剩餘價值
        current_days = self.pricing_plans.get(current_plan, {}).get('days', 1)
        remaining_value = (current_price / current_days) * remaining_days
        
        # 升級價格 = 目標價格 - 剩餘價值
        upgrade_price = max(0, target_price - remaining_value)
        
        return {
            'eligible': True,
            'current_plan': current_plan,
            'target_plan': target_plan,
            'remaining_days': remaining_days,
            'remaining_value': round(remaining_value, 2),
            'upgrade_price': round(upgrade_price, 2)
        }
    
    def generate_referral_code(self, user_id: int) -> str:
        """生成推薦碼"""
        # 使用用戶ID和時間戳生成唯一推薦碼
        data = f"REF_{user_id}_{int(datetime.now().timestamp())}"
        hash_value = hashlib.md5(data.encode()).hexdigest()[:8].upper()
        return f"REF{hash_value}"
    
    def calculate_referral_reward(self, referred_plan: str) -> Dict:
        """計算推薦獎勵"""
        plan_price = self.pricing_plans.get(referred_plan, {}).get('price', 0)
        
        # 推薦獎勵規則
        reward_rates = {
            'trial': 0,      # 試用無獎勵
            'weekly': 0.2,   # 20%
            'monthly': 0.25, # 25%
            'quarterly': 0.3,# 30%
            'yearly': 0.35,  # 35%
            'lifetime': 0.4  # 40%
        }
        
        reward_rate = reward_rates.get(referred_plan, 0)
        reward_amount = plan_price * reward_rate
        
        return {
            'plan': referred_plan,
            'plan_price': plan_price,
            'reward_rate': reward_rate,
            'reward_amount': round(reward_amount, 2)
        }

# 示例：如何使用增強功能
if __name__ == "__main__":
    system = EnhancedActivationSystem()
    
    print("🎯 激活碼系統增強功能演示\n")
    
    # 1. 生成安全激活碼
    code = system.generate_secure_activation_code('monthly', 123456, 'ORDER001')
    print(f"1. 安全激活碼: {code}")
    
    # 2. 計算促銷價格
    promo_price = system.calculate_price_with_promo('yearly', 'LAUNCH50')
    print(f"\n2. 促銷價格計算:")
    print(f"   原價: ${promo_price['base_price']}")
    print(f"   折扣: ${promo_price['discount']}")
    print(f"   最終價格: ${promo_price['final_price']}")
    
    # 3. 批量生成
    batch_codes = system.generate_batch_codes('monthly', 5, 'BATCH001', 789)
    print(f"\n3. 批量生成激活碼:")
    for i, code in enumerate(batch_codes, 1):
        print(f"   {i}. {code}")
    
    # 4. 升級計算
    upgrade = system.check_upgrade_eligibility('monthly', 'yearly', 20)
    print(f"\n4. 升級計算:")
    print(f"   當前方案: {upgrade['current_plan']}")
    print(f"   目標方案: {upgrade['target_plan']}")
    print(f"   剩餘天數: {upgrade['remaining_days']}")
    print(f"   升級價格: ${upgrade['upgrade_price']}")
    
    # 5. 推薦獎勵
    referral_code = system.generate_referral_code(123456)
    reward = system.calculate_referral_reward('yearly')
    print(f"\n5. 推薦系統:")
    print(f"   推薦碼: {referral_code}")
    print(f"   推薦年卡獎勵: ${reward['reward_amount']} ({int(reward['reward_rate']*100)}%)")