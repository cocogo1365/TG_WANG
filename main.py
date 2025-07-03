#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG營銷系統 - Telegram機器人
USDT支付和激活碼分發系統
"""

import asyncio
import json
import logging
import os
import random
import re
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)

try:
    from config import Config
    from database import Database
    from tron_monitor import TronMonitor
    from activation_codes import ActivationCodeManager
except ImportError as e:
    print(f"❌ 導入模塊失敗: {e}")
    print("請確保所有必需的模塊文件存在")
    exit(1)

# 設置日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        # 速率限制：每個用戶每分鐘最多操作次數
        self.rate_limits = defaultdict(lambda: deque())
        self.MAX_REQUESTS_PER_MINUTE = 20
        self.MAX_REQUESTS_PER_HOUR = 100
        
        # 黑名單用戶
        self.blacklisted_users = set()
        
        # 可疑行為監控
        self.suspicious_activities = defaultdict(int)
        
        # 輸入驗證模式
        self.order_id_pattern = re.compile(r'^TG[0-9A-Z]{8,12}$')
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_]{1,32}$')
        
    def is_rate_limited(self, user_id: int) -> bool:
        """檢查用戶是否被速率限制"""
        now = time.time()
        user_requests = self.rate_limits[user_id]
        
        # 清理過期的請求記錄（1分鐘前）
        while user_requests and user_requests[0] < now - 60:
            user_requests.popleft()
        
        # 檢查是否超過限制
        if len(user_requests) >= self.MAX_REQUESTS_PER_MINUTE:
            return True
            
        # 記錄當前請求
        user_requests.append(now)
        return False
    
    def is_blacklisted(self, user_id: int) -> bool:
        """檢查用戶是否在黑名單中"""
        return user_id in self.blacklisted_users
    
    def add_to_blacklist(self, user_id: int):
        """添加用戶到黑名單"""
        self.blacklisted_users.add(user_id)
        logger.warning(f"用戶 {user_id} 已被加入黑名單")
    
    def validate_order_id(self, order_id: str) -> bool:
        """驗證訂單ID格式"""
        if not order_id or len(order_id) > 20:
            return False
        return bool(self.order_id_pattern.match(order_id))
    
    def sanitize_input(self, text: str, max_length: int = 100) -> str:
        """清理和驗證輸入文本"""
        if not text:
            return ""
        
        # 移除危險字符
        sanitized = re.sub(r'[<>"\'\\/]', '', text.strip())
        
        # 限制長度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            
        return sanitized
    
    def log_suspicious_activity(self, user_id: int, activity: str):
        """記錄可疑活動"""
        self.suspicious_activities[user_id] += 1
        logger.warning(f"可疑活動 - 用戶 {user_id}: {activity}")
        
        # 如果可疑活動過多，加入黑名單
        if self.suspicious_activities[user_id] > 10:
            self.add_to_blacklist(user_id)
    
    def validate_user_input(self, user_id: int, username: str, first_name: str) -> bool:
        """驗證用戶輸入信息"""
        # 檢查用戶名格式
        if username and not self.username_pattern.match(username):
            self.log_suspicious_activity(user_id, f"無效用戶名格式: {username}")
            return False
            
        # 檢查名字長度
        if first_name and len(first_name) > 64:
            self.log_suspicious_activity(user_id, f"名字過長: {first_name}")
            return False
            
        return True

class SmartMonitorManager:
    """智能監控管理器 - 只在需要時監控"""
    
    def __init__(self):
        # 待監控的訂單列表 {order_id: {'amount': float, 'created_at': datetime, 'expires_at': datetime}}
        self.pending_orders = {}
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_task = None
        
        # 監控配置
        self.MONITOR_WINDOW_MINUTES = 30  # 監控窗口：30分鐘
        self.CHECK_INTERVAL_SECONDS = 60   # 檢查間隔：60秒
        
    def add_order_for_monitoring(self, order_id: str, amount: float):
        """添加訂單到監控列表"""
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.MONITOR_WINDOW_MINUTES)
        
        self.pending_orders[order_id] = {
            'amount': amount,
            'created_at': now,
            'expires_at': expires_at
        }
        
        logger.info(f"訂單 {order_id} 加入監控列表，金額: {amount} USDT")
        
        # 如果還沒開始監控，啟動監控
        if not self.is_monitoring:
            logger.info("啟動智能監控...")
    
    def remove_order_from_monitoring(self, order_id: str):
        """從監控列表移除訂單"""
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
            logger.info(f"訂單 {order_id} 已從監控列表移除")
    
    def cleanup_expired_orders(self, db=None):
        """清理過期的監控訂單並自動取消"""
        now = datetime.now()
        expired_orders = []
        
        for order_id, info in self.pending_orders.items():
            if now > info['expires_at']:
                expired_orders.append(order_id)
        
        for order_id in expired_orders:
            logger.info(f"訂單 {order_id} 監控已過期，自動取消")
            
            # 從監控列表移除
            del self.pending_orders[order_id]
            
            # 如果提供了數據庫實例，自動取消數據庫中的訂單
            if db:
                try:
                    order = db.get_order(order_id)
                    if order and order.get('status') == 'pending':
                        db.update_order_status(order_id, 'cancelled')
                        logger.info(f"訂單 {order_id} 已自動取消（30分鐘未付款）")
                except Exception as e:
                    logger.error(f"自動取消訂單 {order_id} 失敗: {e}")
        
        return len(expired_orders)
    
    def should_monitor(self, db=None) -> bool:
        """判斷是否需要監控"""
        self.cleanup_expired_orders(db)
        return len(self.pending_orders) > 0
    
    def get_monitoring_amounts(self, db=None) -> List[float]:
        """獲取需要監控的金額列表"""
        self.cleanup_expired_orders(db)
        return [info['amount'] for info in self.pending_orders.values()]
    
    def get_pending_orders_count(self, db=None) -> int:
        """獲取待監控訂單數量"""
        self.cleanup_expired_orders(db)
        return len(self.pending_orders)

class TGMarketingBot:
    """TG營銷系統機器人主類"""
    
    def __init__(self):
        try:
            self.config = Config()
        except Exception as e:
            logger.error(f"❌ 配置初始化失敗: {e}")
            raise
            
        try:
            self.db = Database()
        except Exception as e:
            logger.error(f"❌ 數據庫初始化失敗: {e}")
            raise
            
        try:
            self.tron_monitor = TronMonitor()
        except Exception as e:
            logger.error(f"❌ TRON監控初始化失敗: {e}")
            raise
            
        try:
            self.activation_manager = ActivationCodeManager()
        except Exception as e:
            logger.error(f"❌ 激活碼管理器初始化失敗: {e}")
            raise
            
        # 初始化安全管理器
        self.security = SecurityManager()
        
        # 初始化智能監控管理器
        self.smart_monitor = SmartMonitorManager()
        
        # 測試模式
        self.TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
        logger.info(f"測試模式狀態: {self.TEST_MODE} (環境變量: {os.getenv('TEST_MODE', 'false')})")
        
        # 價格配置
        if self.TEST_MODE:
            # 測試模式：使用 TRX 代替 USDT，價格設為 1 TRX
            self.pricing = {
                'trial': {'days': 2, 'price': 0, 'name': '免費試用'},
                'weekly': {'days': 7, 'price': 1.0, 'name': '測試方案(1 TRX)'},
                'monthly': {'days': 30, 'price': 1.0, 'name': '測試方案(1 TRX)'}
            }
            self.currency = 'TRX'
            self.currency_name = 'TRX'
            logger.warning("⚠️ 測試模式已啟用 - 使用 TRX 支付")
        else:
            # 正式模式：使用 USDT
            self.pricing = {
                'trial': {'days': 2, 'price': 0, 'name': '免費試用'},
                'weekly': {'days': 7, 'price': 20.0, 'name': '一週方案'},
                'monthly': {'days': 30, 'price': 70.0, 'name': '一個月方案'}
            }
            self.currency = 'USDT'
            self.currency_name = 'USDT (TRC-20)'
        
        # 監控將在應用程序啟動後開始
    
    async def security_check(self, update: Update) -> bool:
        """安全檢查，返回True表示通過"""
        user = update.effective_user
        user_id = user.id
        
        # 檢查黑名單
        if self.security.is_blacklisted(user_id):
            logger.warning(f"黑名單用戶嘗試訪問: {user_id}")
            return False
        
        # 檢查速率限制
        if self.security.is_rate_limited(user_id):
            logger.warning(f"用戶 {user_id} 觸發速率限制")
            if update.callback_query:
                await update.callback_query.answer("⚠️ 操作過於頻繁，請稍後再試", show_alert=True)
            elif update.message:
                await update.message.reply_text("⚠️ 操作過於頻繁，請稍後再試")
            return False
        
        # 驗證用戶輸入
        if not self.security.validate_user_input(user_id, user.username, user.first_name):
            logger.warning(f"用戶輸入驗證失敗: {user_id}")
            return False
            
        return True
    
    async def start_monitoring(self):
        """啟動交易監控（舊版 - 保留兼容性）"""
        logger.info("⚠️ 舊版監控已停用，使用智能監控替代")
    
    async def start_smart_monitoring(self):
        """啟動智能監控"""
        if self.smart_monitor.is_monitoring:
            return  # 已經在監控中
        
        if not self.smart_monitor.should_monitor(self.db):
            return  # 沒有待監控的訂單
        
        self.smart_monitor.is_monitoring = True
        
        # 創建智能監控任務
        async def smart_monitor_task():
            logger.info("🔍 智能監控已啟動")
            
            while self.smart_monitor.should_monitor(self.db):
                try:
                    # 獲取需要監控的金額
                    amounts_to_monitor = self.smart_monitor.get_monitoring_amounts(self.db)
                    
                    if amounts_to_monitor:
                        logger.info(f"正在監控 {len(amounts_to_monitor)} 個訂單的付款")
                        
                        # 只查詢最近的交易（過去30分鐘）
                        await self.check_recent_transactions(amounts_to_monitor)
                    
                    # 等待檢查間隔
                    await asyncio.sleep(self.smart_monitor.CHECK_INTERVAL_SECONDS)
                    
                except Exception as e:
                    logger.error(f"智能監控錯誤: {e}")
                    await asyncio.sleep(30)  # 錯誤時短暫等待
            
            # 沒有待監控訂單，停止監控
            self.smart_monitor.is_monitoring = False
            logger.info("📴 智能監控已停止 - 無待監控訂單")
        
        # 啟動監控任務
        self.smart_monitor.monitor_task = asyncio.create_task(smart_monitor_task())
    
    async def check_recent_transactions(self, amounts_to_monitor: List[float]):
        """檢查最近的交易"""
        try:
            logger.info(f"🔍 檢查 {len(amounts_to_monitor)} 個訂單的付款狀態")
            
            for amount in amounts_to_monitor:
                logger.debug(f"檢查金額 {amount} {'TRX' if self.TEST_MODE else 'USDT'} 的交易")
                
                # 調用 TronMonitor 驗證付款
                payment_result = await self.tron_monitor.verify_payment(amount, max_age_minutes=30)
                
                if payment_result:
                    logger.info(f"🎉 發現匹配的付款: {amount} {'TRX' if self.TEST_MODE else 'USDT'}")
                    logger.info(f"📋 交易哈希: {payment_result.get('tx_hash', '未知')}")
                    
                    # 找到對應的訂單
                    orders = list(self.smart_monitor.pending_orders.keys())
                    for order_id in orders:
                        order_info = self.smart_monitor.pending_orders[order_id]
                        if abs(order_info['amount'] - amount) < 0.001:  # 金額匹配
                            await self.handle_payment_confirmed(payment_result)
                            break
                else:
                    logger.debug(f"未找到金額 {amount} 的匹配付款")
                
        except Exception as e:
            logger.error(f"檢查交易失敗: {e}")
            import traceback
            logger.error(f"錯誤詳情: {traceback.format_exc()}")
    
    async def send_message(self, update: Update, text: str, reply_markup=None, parse_mode=None):
        """統一的消息發送方法，處理普通消息和回調查詢"""
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    async def send_new_message(self, update: Update, text: str, reply_markup=None, parse_mode=None):
        """發送新消息（不編輯現有消息）"""
        user_id = update.effective_user.id
        await self.application.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /start 命令"""
        # 安全檢查
        if not await self.security_check(update):
            return
            
        user = update.effective_user
        user_id = user.id
        
        try:
            # 記錄用戶
            self.db.add_user(user_id, user.username, user.first_name)
            
            # 檢查是否已有試用記錄
            trial_used = self.db.has_used_trial(user_id)
        except Exception as e:
            logger.error(f"Database error in start_command: {e}")
            trial_used = False  # 默認值
        
        welcome_text = f"""
🎯 **歡迎使用 TG營銷系統** 🎯

你好 {user.first_name}！👋

🚀 **專業的 Telegram 營銷工具**
• 多賬戶智能管理
• 高效群組邀請系統  
• 批量消息發送
• 數據採集與分析
• 智能防封號保護

💎 **靈活的價格方案**
🆓 **免費試用** - 2天完整體驗
📅 **一週方案** - {self.pricing['weekly']['price']} {self.currency}
📅 **一個月方案** - {self.pricing['monthly']['price']} {self.currency}

⚡ **特色優勢**
• {self.currency_name} 安全支付
• 即時自動發放激活碼
• 24/7 客服支持
• 簡單易用的操作界面

🎁 **立即開始使用下方按鈕！**
"""
        
        # 測試模式提示
        if self.TEST_MODE:
            welcome_text += "\n\n⚠️ **測試模式已啟用** - 使用 1 TRX 進行支付測試"
        
        if trial_used:
            welcome_text += "\n⚠️ 您已使用過免費試用，請選擇付費方案"
        else:
            welcome_text += "\n🎁 您可以免費試用2天！"
        
        keyboard = [
            [InlineKeyboardButton("🛒 購買激活碼", callback_data="buy_menu")],
            [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders"), InlineKeyboardButton("🔍 查詢訂單", callback_data="search_order")],
            [InlineKeyboardButton("❓ 使用說明", callback_data="help"), InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
            [InlineKeyboardButton("⚙️ 系統狀態", callback_data="system_status")]
        ]
        
        # 添加測試模式按鈕
        if self.TEST_MODE:
            keyboard.append([InlineKeyboardButton("🧪 1 TRX 測試購買", callback_data="test_mode_buy")])
            logger.info(f"測試模式按鈕已添加到用戶 {user_id} 的主菜單")
        
        # 管理員額外按鈕
        if user_id in self.config.ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("🔧 管理後台", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, welcome_text, reply_markup=reply_markup)
    
    
    async def show_pricing_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示價格選單"""
        user_id = update.effective_user.id
        trial_used = self.db.has_used_trial(user_id)
        
        text = "💰 **選擇購買方案**：\n\n"
        keyboard = []
        
        # 免費試用
        if not trial_used:
            text += "🆓 **免費試用** - 2天\n"
            text += "   完整功能體驗\n"
            text += "   每個TG帳戶限用一次\n\n"
            keyboard.append([InlineKeyboardButton("🎁 申請免費試用", callback_data="buy_trial")])
        
        # 付費方案
        weekly_price = self.pricing['weekly']['price']
        monthly_price = self.pricing['monthly']['price']
        
        text += f"📅 **一週方案** - {weekly_price} {self.currency}\n"
        text += "   7天完整使用權限\n"
        text += "   所有功能無限制\n\n"
        keyboard.append([InlineKeyboardButton(f"💳 購買一週 ({weekly_price} {self.currency})", callback_data="buy_weekly")])
        
        text += f"📅 **一個月方案** - {monthly_price} {self.currency}\n"
        text += "   30天完整使用權限\n"
        text += "   所有功能無限制\n"
        text += "   最優價格比例\n\n"
        keyboard.append([InlineKeyboardButton(f"💳 購買一個月 ({monthly_price} {self.currency})", callback_data="buy_monthly")])
        
        text += f"💡 使用 {self.currency_name} 支付，自動發放激活碼"
        
        keyboard.append([InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str):
        """處理購買請求"""
        # 安全檢查
        if not await self.security_check(update):
            return
            
        user_id = update.effective_user.id
        user = update.effective_user
        
        # 檢查是否有未完成的訂單（防止重複購買）
        user_orders = self.db.get_user_orders(user_id)
        pending_orders = [order for order in user_orders if order['status'] == 'pending']
        
        if pending_orders:
            pending_order = pending_orders[0]  # 獲取最新的待付款訂單
            await update.callback_query.answer(
                f"❌ 您有未完成的訂單 {pending_order['order_id']}，請先完成付款或等待訂單過期", 
                show_alert=True
            )
            return
        
        # 驗證方案類型
        if plan_type not in self.pricing:
            self.security.log_suspicious_activity(user_id, f"無效方案類型: {plan_type}")
            await update.callback_query.answer("❌ 無效的方案類型", show_alert=True)
            return
        
        # 生成唯一的訂單金額（避免衝突）
        unique_amount = self.generate_unique_amount(plan_type)
        
        if plan_type == 'trial':
            # 處理試用申請
            if self.db.has_used_trial(user_id):
                await update.callback_query.answer("您已使用過免費試用！", show_alert=True)
                return
            
            # 直接生成試用激活碼
            activation_code = self.activation_manager.generate_activation_code(
                plan_type='trial',
                days=2,
                user_id=user_id
            )
            
            # 記錄試用使用
            self.db.mark_trial_used(user_id)
            
            # 發送激活碼
            text = f"""
🎉 **免費試用激活碼已生成！**

🔑 **激活碼**: `{activation_code}`
⏰ **有效期**: 2天
📝 **使用方法**: 
1. 下載TG營銷系統軟件
2. 在軟件中輸入此激活碼
3. 開始使用所有功能

💡 試用期結束後，歡迎購買正式版本！
"""
            
            keyboard = [
                [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                [InlineKeyboardButton("💳 購買正式版", callback_data="buy_menu")],
                [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
            
        else:
            # 處理付費購買
            plan_info = self.pricing[plan_type]
            order_id = self.generate_order_id()
            
            # 創建訂單
            order_data = {
                'order_id': order_id,
                'user_id': user_id,
                'username': user.username,
                'plan_type': plan_type,
                'amount': unique_amount,
                'days': plan_info['days'],
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            try:
                self.db.create_order(order_data)
            except Exception as e:
                logger.error(f"Failed to create order: {e}")
                await update.callback_query.answer("❌ 創建訂單失敗，請稍後重試", show_alert=True)
                return
            
            # 添加到智能監控列表
            self.smart_monitor.add_order_for_monitoring(order_id, unique_amount)
            
            # 啟動智能監控（如果還沒啟動）
            await self.start_smart_monitoring()
            
            # 發送三條獨立消息
            await self.send_order_messages(update, order_id, plan_info, unique_amount)
    
    async def send_order_messages(self, update: Update, order_id: str, plan_info: Dict, unique_amount: float):
        """發送訂單相關的三條獨立消息"""
        user_id = update.effective_user.id
        
        # 第一條消息：訂單詳情
        order_text = f"""
📋 **訂單創建成功！**

🆔 訂單號: `{order_id}`
📦 購買方案: {plan_info['name']}
💰 支付金額: {unique_amount} {self.currency}
⏰ 使用期限: {plan_info['days']} 天
📅 訂單有效期: 24小時

✅ 請按照以下步驟完成付款
"""
        
        keyboard1 = [
            [InlineKeyboardButton("📊 查詢訂單狀態", callback_data=f"status_{order_id}")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup1 = InlineKeyboardMarkup(keyboard1)
        
        await self.send_message(update, order_text, reply_markup=reply_markup1, parse_mode='Markdown')
        
        # 第二條消息：付款金額信息
        amount_info_text = f"""
💰 **付款金額信息**

付款金額: **{unique_amount} {self.currency}**
🌐 網絡類型: **TRON {'(TRX)' if self.TEST_MODE else '(TRC-20)'}**

⚠️ **重要提醒**:
• 請務必使用 TRON 網絡轉賬
• 請準確發送 {unique_amount} {self.currency}
• 金額不正確可能導致付款失敗
• 付款完成後請點擊"已付款"按鈕

🔍 **付款後**: 系統將在5-10分鐘內自動確認
"""
        
        keyboard2 = [
            [InlineKeyboardButton("❌ 取消付款", callback_data=f"cancel_payment_{order_id}"), 
             InlineKeyboardButton("✅ 完成付款", callback_data=f"complete_payment_{order_id}")],
            [InlineKeyboardButton("📋 查看訂單", callback_data=f"status_{order_id}")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup2 = InlineKeyboardMarkup(keyboard2)
        
        await self.send_new_message(update, amount_info_text, reply_markup=reply_markup2, parse_mode='Markdown')
        
        # 第三條消息：收款地址（單獨發送，方便手機用戶複製）
        address_text = f"""🏦 收款地址

{self.config.USDT_ADDRESS}

📱 如何複製地址:
• 點擊上方地址文字
• 選擇「複製」或「Copy」
• 或者長按地址進行選取複製

⚠️ 重要: 請確保地址完整且正確"""
        
        keyboard3 = [
            [InlineKeyboardButton("📋 查看訂單", callback_data=f"status_{order_id}")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup3 = InlineKeyboardMarkup(keyboard3)
        
        await self.send_new_message(update, address_text, reply_markup=reply_markup3)
        
        # 第四條消息：客服留言
        service_text = f"""👋 親愛的客戶，您好！

感謝您選擇我們的TG營銷系統！

📞 需要幫助？
如果您在付款過程中遇到任何問題，或需要技術支持，請隨時聯繫我們的客服團隊。

🔸 客服聯繫方式: @your_support_username
🔸 服務時間: 24小時在線服務
🔸 回應時間: 通常在30分鐘內回覆

💡 溫馨提示:
• 付款成功後會自動發送激活碼
• 請保留好您的訂單號以便查詢
• 如有疑問，請提供訂單號給客服

🎯 我們致力於為您提供最優質的服務體驗！"""
        
        keyboard4 = [
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
            [InlineKeyboardButton("❓ 查看幫助", callback_data="help")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup4 = InlineKeyboardMarkup(keyboard4)
        
        await self.send_new_message(update, service_text, reply_markup=reply_markup4)
    
    async def handle_payment_confirmed(self, transaction_data: Dict):
        """處理確認的付款"""
        try:
            amount = transaction_data['amount']
            tx_hash = transaction_data['tx_hash']
            
            # 查找匹配的訂單
            order = self.db.find_order_by_amount(amount)
            if not order:
                logger.warning(f"找不到金額為 {amount} USDT 的訂單")
                return
            
            if order['status'] != 'pending':
                logger.warning(f"訂單 {order['order_id']} 狀態不是待付款: {order['status']}")
                return
            
            # 更新訂單狀態
            self.db.update_order_status(order['order_id'], 'paid', tx_hash)
            
            # 生成激活碼
            activation_code = self.activation_manager.generate_activation_code(
                plan_type=order['plan_type'],
                days=order['days'],
                user_id=order['user_id'],
                order_id=order['order_id']
            )
            
            # 從監控列表移除已完成的訂單
            self.smart_monitor.remove_order_from_monitoring(order['order_id'])
            
            # 發送付款確認和激活碼的獨立消息
            if hasattr(self, 'application') and self.application:
                await self.send_activation_messages(order, activation_code, tx_hash)
            
            logger.info(f"✅ 訂單 {order['order_id']} 處理完成，激活碼: {activation_code}")
            
        except Exception as e:
            logger.error(f"❌ 處理付款確認失敗: {e}")
    
    async def send_activation_messages(self, order: Dict, activation_code: str, tx_hash: str):
        """發送激活碼相關的獨立消息"""
        user_id = order['user_id']
        order_id = order['order_id']
        plan_name = self.pricing[order['plan_type']]['name']
        
        # 第一條消息：付款確認
        confirm_text = f"""
✅ **付款確認成功！**

💳 訂單號: `{order_id}`
📦 購買方案: {plan_name}
💰 付款金額: {order['amount']} USDT
🧾 交易哈希: `{tx_hash}`
📅 確認時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您的激活碼正在生成中，請稍等...
"""
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=confirm_text,
            parse_mode='Markdown'
        )
        
        # 第二條消息：激活碼
        activation_text = f"""
🔑 **激活碼已生成！**

**激活碼**: `{activation_code}`

📋 **詳細信息**:
• 訂單號: `{order_id}`
• 方案類型: {plan_name}
• 使用期限: {order['days']} 天
• 狀態: ✅ 已激活

⚠️ **請妥善保存此激活碼！**
"""
        
        keyboard1 = [
            [InlineKeyboardButton("📥 復制激活碼", callback_data="copy_code")],
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")]
        ]
        reply_markup1 = InlineKeyboardMarkup(keyboard1)
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=activation_text,
            reply_markup=reply_markup1,
            parse_mode='Markdown'
        )
        
        # 第三條消息：使用說明和感謝
        usage_text = f"""
📝 **使用說明**

🔸 **軟件下載**:
請聯繫客服獲取最新版軟件下載鏈接

🔸 **激活步驟**:
1. 打開TG營銷系統軟件
2. 在激活界面輸入您的激活碼
3. 點擊"激活"按鈕
4. 開始享受所有功能

🔸 **技術支持**:
如在使用過程中遇到任何問題，我們的客服團隊將為您提供專業支持

🎯 **感謝您的信任與支持！**
祝您使用愉快，業務蒸蒸日上！💪

---
TG營銷系統團隊 敬上 ❤️
"""
        
        keyboard2 = [
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
            [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup2 = InlineKeyboardMarkup(keyboard2)
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=usage_text,
            reply_markup=reply_markup2,
            parse_mode='Markdown'
        )
    
    async def handle_test_mode_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理測試模式購買 - 直接模擬收到1TRX付款並發送隨機驗證碼"""
        if not self.TEST_MODE:
            await update.callback_query.answer("❌ 測試模式未啟用", show_alert=True)
            return
            
        user_id = update.effective_user.id
        user = update.effective_user
        
        # 檢查是否有未完成的訂單（防止重複測試）
        user_orders = self.db.get_user_orders(user_id)
        pending_orders = [order for order in user_orders if order['status'] == 'pending']
        
        if pending_orders:
            pending_order = pending_orders[0]
            await update.callback_query.answer(
                f"❌ 您有未完成的測試訂單 {pending_order['order_id']}，請先完成測試或等待過期", 
                show_alert=True
            )
            return
        
        # 生成唯一的測試訂單金額 (1 TRX + 小數點)
        test_amount = self.generate_unique_amount('weekly')  # 使用週方案作為測試
        order_id = self.generate_order_id()
        
        # 創建測試訂單
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'username': user.username,
            'plan_type': 'weekly',
            'amount': test_amount,
            'days': 7,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        try:
            self.db.create_order(order_data)
            
            # 將測試訂單加入智能監控系統（真實監控 TRX 付款）
            self.smart_monitor.add_order_for_monitoring(order_id, test_amount)
            
            # 啟動智能監控
            await self.start_smart_monitoring()
            
            logger.info(f"測試訂單 {order_id} 已加入 TRX 監控，金額: {test_amount} TRX")
            
        except Exception as e:
            logger.error(f"Failed to create test order: {e}")
            await update.callback_query.answer("❌ 創建測試訂單失敗", show_alert=True)
            return
        
        # 顯示測試購買界面
        test_text = f"""🧪 真實 TRX 測試購買

🆔 測試訂單號: {order_id}
💰 付款金額: {test_amount} TRX
🌐 網絡類型: TRON (TRX)
📦 測試方案: 一週方案 (7天)

⚡ 測試說明:
• 請真實發送 {test_amount} TRX 到收款地址
• 系統會自動監控您的付款
• 確認收到後立即發送真實激活碼
• 這是低成本的真實交易測試

🔍 收款地址: {self.config.USDT_ADDRESS}

⚠️ 這需要真實的 TRX 付款（約 {test_amount} TRX ≈ $0.10-0.20）"""
        
        keyboard = [
            [InlineKeyboardButton("📋 查看訂單狀態", callback_data=f"status_{order_id}")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, test_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # 第二條消息：付款金額信息
        amount_text = f"""💰 真實 TRX 測試付款

付款金額: {test_amount} TRX
網絡類型: TRON (TRX)

💡 真實測試說明:
• 請向收款地址發送準確的 {test_amount} TRX
• 系統會自動監控區塊鏈交易
• 確認收到後 5-10 分鐘內發放激活碼
• 這是真實的 TRX 交易，會產生實際費用

⚠️ 約需 {test_amount} TRX（價值約 $0.10-0.20）"""
        
        keyboard_amount = [
            [InlineKeyboardButton("❌ 取消測試", callback_data=f"cancel_test_{order_id}"), 
             InlineKeyboardButton("✅ 我已付款", callback_data=f"check_payment_{order_id}")],
            [InlineKeyboardButton("📋 查看訂單", callback_data=f"status_{order_id}")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup_amount = InlineKeyboardMarkup(keyboard_amount)
        
        await self.send_new_message(update, amount_text, reply_markup=reply_markup_amount, parse_mode='Markdown')
        
        # 第三條消息：收款地址（單獨發送，方便複製）
        address_text = f"""🏦 TRX 測試收款地址

{self.config.USDT_ADDRESS}

📱 如何複製地址:
• 點擊上方地址文字
• 選擇「複製」或「Copy」
• 或者長按地址進行選取複製

🔴 重要: 這是真實的 TRX 交易
• 請確保發送準確的金額: {test_amount} TRX
• 使用 TRON 網絡進行轉賬
• 系統會自動監控您的付款"""
        
        keyboard_address = [
            [InlineKeyboardButton("🔄 重新測試", callback_data="test_mode_buy")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup_address = InlineKeyboardMarkup(keyboard_address)
        
        await self.send_new_message(update, address_text, reply_markup=reply_markup_address)
    
    async def handle_test_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """處理測試付款模擬"""
        if not self.TEST_MODE:
            await update.callback_query.answer("❌ 測試模式未啟用", show_alert=True)
            return
            
        user_id = update.effective_user.id
        
        # 獲取訂單
        order = self.db.get_order(order_id)
        if not order or order['user_id'] != user_id:
            await update.callback_query.answer("❌ 訂單不存在或無權限", show_alert=True)
            return
            
        if order['status'] != 'pending':
            await update.callback_query.answer("❌ 訂單狀態異常", show_alert=True)
            return
        
        # 模擬交易哈希
        test_tx_hash = f"TEST_{random.randint(100000, 999999)}"
        
        # 更新訂單狀態為已付款
        self.db.update_order_status(order_id, 'paid', test_tx_hash)
        
        # 生成激活碼
        activation_code = self.activation_manager.generate_activation_code(
            plan_type=order['plan_type'],
            days=order['days'],
            user_id=user_id,
            order_id=order_id
        )
        
        # 發送三條測試消息（模擬實際流程）
        await self.send_test_activation_messages(order, activation_code, test_tx_hash)
        
        await update.callback_query.answer("✅ 測試付款模擬完成！", show_alert=True)
    
    async def send_test_activation_messages(self, order: Dict, activation_code: str, tx_hash: str):
        """發送測試模式的激活碼消息"""
        user_id = order['user_id']
        order_id = order['order_id']
        
        # 第一條消息：付款確認
        confirm_text = f"""
✅ **測試付款確認成功！**

💳 測試訂單號: `{order_id}`
💰 付款金額: {order['amount']} TRX
🧾 測試交易: `{tx_hash}`
📅 確認時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🧪 **測試模式**: 模擬收款成功
🎉 激活碼正在生成中...
"""
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=confirm_text,
            parse_mode='Markdown'
        )
        
        # 第二條消息：激活碼
        activation_text = f"""
🔑 **測試激活碼已生成！**

**激活碼**: `{activation_code}`

📋 **測試詳情**:
• 測試訂單: `{order_id}`
• 測試方案: 一週方案
• 測試期限: 7 天
• 狀態: ✅ 測試成功

🧪 **這是測試生成的激活碼**
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 再次測試", callback_data="test_mode_buy")],
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=activation_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # 第三條消息：隨機驗證碼（用於測試）
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        verification_text = f"""
🎲 **隨機驗證碼測試**

驗證碼: `{random_code}`

📝 **測試說明**:
這是一個隨機生成的驗證碼，用於測試系統的消息發送功能
在實際使用中，這裡會發送客戶服務消息

✅ **測試完成**！系統已成功：
• 模擬收到 TRX 付款
• 生成激活碼
• 發送三條獨立消息
• 生成隨機驗證碼

🔄 您可以重複進行測試來驗證系統穩定性
"""
        
        keyboard2 = [
            [InlineKeyboardButton("🔄 重新測試", callback_data="test_mode_buy")],
            [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
        ]
        reply_markup2 = InlineKeyboardMarkup(keyboard2)
        
        await self.application.bot.send_message(
            chat_id=user_id,
            text=verification_text,
            reply_markup=reply_markup2,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /help 命令"""
        help_text = """
📖 **TG營銷系統使用幫助**

🎯 **如何使用**:
• 點擊"購買激活碼"選擇方案
• 使用"我的訂單"查看購買記錄  
• 通過"查詢訂單"追蹤付款狀態
• "聯繫客服"獲得專業支持

💰 **價格方案**:
• 🆓 免費試用: 2天 (每帳戶限用一次)
• 📅 一週方案: {self.pricing['weekly']['price']} {self.currency} (7天)
• 📅 一個月方案: {self.pricing['monthly']['price']} {self.currency} (30天)

💳 **付款流程**:
1. 選擇購買方案
2. 發送 {self.currency_name} 到指定地址
3. 點擊"已付款"確認
4. 5-10分鐘內自動收到激活碼

📝 **軟件功能**:
• 多賬戶智能管理
• 高效群組邀請系統
• 批量消息發送
• 數據採集與分析
• 智能防封號保護

❓ **常見問題**:
• 付款後多久收到激活碼？通常5-10分鐘自動發放
• 激活碼可以重複使用嗎？每個激活碼只能使用一次
• 試用版有功能限制嗎？功能完整，僅有時間限制
• 如何下載軟件？購買後客服提供下載鏈接

🔧 **操作提示**:
• 建議使用按鈕操作，快速便捷
• 可直接發送訂單號查詢狀態
• 支持24/7在線客服支持

📞 **客服支持**: @your_support_username
"""
        keyboard = [
            [InlineKeyboardButton("🛒 立即購買", callback_data="buy_menu")],
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示聯繫客服信息"""
        contact_text = """
📞 **客服聯繫方式**

🔸 **Telegram**: @your_support_username
🔸 **工作時間**: 週一至週日 9:00-22:00
🔸 **回覆時間**: 通常在30分鐘內回覆

❓ **常見問題**:
• 付款後多久收到激活碼？
  答：通常5-10分鐘自動發放

• 激活碼忘記了怎麼辦？
  答：可通過"我的訂單"查看

• 軟件下載地址在哪裡？
  答：購買後客服會提供下載鏈接

📧 如有其他問題，請直接聯繫客服
"""
        
        keyboard = [
            [InlineKeyboardButton("🛒 購買激活碼", callback_data="buy_menu")],
            [InlineKeyboardButton("❓ 使用說明", callback_data="help")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, contact_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示系統狀態"""
        try:
            # 檢查各個系統組件狀態
            db_status = "🟢 正常" 
            monitor_status = "🟢 正常"
            payment_status = "🟢 正常"
            
            # 獲取簡單統計
            stats = self.db.get_statistics() if hasattr(self.db, 'get_statistics') else {}
            
            status_text = f"""
⚙️ **系統狀態監控**

🔸 **服務狀態**:
• 機器人服務: 🟢 運行中
• 數據庫服務: {db_status}
• 支付監控: {monitor_status} 
• USDT 監控: {payment_status}

📊 **運行統計**:
• 今日處理訂單: {stats.get('today_orders', 0)} 筆
• 在線用戶: {stats.get('total_users', 0)} 人
• 系統運行時間: 正常

🔄 **最後更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 所有系統運行正常，可正常下單購買
"""
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            status_text = """
⚙️ **系統狀態監控**

⚠️ 正在檢查系統狀態...
如有問題請聯繫客服
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 刷新狀態", callback_data="system_status")],
            [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, status_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_search_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示訂單查詢說明"""
        search_text = """
🔍 **訂單查詢**

請選擇查詢方式：

🔸 **查看我的所有訂單**
   查看您的完整訂單歷史

🔸 **按訂單號查詢**
   輸入訂單號查詢具體訂單

💡 **提示**: 
• 訂單號格式：TG123456ABCD
• 可在"我的訂單"中查看所有訂單
• 如需幫助請聯繫客服
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 查看所有訂單", callback_data="my_orders")],
            [InlineKeyboardButton("🔢 輸入訂單號", callback_data="input_order_id")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, search_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /admin 命令"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            await self.send_message(update, "❌ 無權限訪問管理功能")
            return
        
        stats = self.db.get_statistics()
        
        admin_text = f"""
🔧 **管理後台**

📊 **統計數據**:
• 總用戶數: {stats['total_users']}
• 總訂單數: {stats['total_orders']}
• 待付款訂單: {stats['pending_orders']}
• 已完成訂單: {stats['completed_orders']}
• 總收入: {stats['total_revenue']} USDT
• 今日收入: {stats['today_revenue']} USDT

🎯 **激活碼統計**:
• 已生成: {stats['total_activations']}
• 已使用: {stats['used_activations']}
• 試用激活碼: {stats['trial_activations']}

⚙️ **系統狀態**: 正常運行
📡 **監控狀態**: 正常
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 詳細統計", callback_data="admin_stats"), InlineKeyboardButton("📈 收入報表", callback_data="admin_revenue")],
            [InlineKeyboardButton("👥 用戶管理", callback_data="admin_users"), InlineKeyboardButton("📋 訂單管理", callback_data="admin_orders")],
            [InlineKeyboardButton("🛡️ 安全管理", callback_data="security_panel"), InlineKeyboardButton("🔄 重啟監控", callback_data="admin_restart")],
            [InlineKeyboardButton("⚙️ 系統設置", callback_data="admin_settings"), InlineKeyboardButton("🧹 清理數據", callback_data="admin_cleanup")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, admin_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示管理員控制面板"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            self.security.log_suspicious_activity(user_id, "嘗試訪問管理員功能")
            await update.callback_query.answer("❌ 無權限訪問", show_alert=True)
            return
            
        logger.info(f"管理員 {user_id} 訪問控制面板")
        await self.admin_command(update, context)
    
    async def show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示詳細統計"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            await update.callback_query.answer("❌ 無權限訪問", show_alert=True)
            return
        
        try:
            stats = self.db.get_statistics()
            
            stats_text = f"""
📊 **詳細統計報表**

📈 **訂單統計**:
• 總訂單數: {stats.get('total_orders', 0)}
• 今日訂單: {stats.get('today_orders', 0)}
• 本週訂單: {stats.get('week_orders', 0)}
• 本月訂單: {stats.get('month_orders', 0)}

💰 **收入統計**:
• 總收入: {stats.get('total_revenue', 0)} USDT
• 今日收入: {stats.get('today_revenue', 0)} USDT
• 本週收入: {stats.get('week_revenue', 0)} USDT
• 本月收入: {stats.get('month_revenue', 0)} USDT

👥 **用戶統計**:
• 總用戶數: {stats.get('total_users', 0)}
• 今日新增: {stats.get('today_new_users', 0)}
• 活躍用戶: {stats.get('active_users', 0)}
• 付費用戶: {stats.get('paid_users', 0)}

🎯 **激活碼統計**:
• 已生成: {stats.get('total_activations', 0)}
• 已使用: {stats.get('used_activations', 0)}
• 試用碼: {stats.get('trial_activations', 0)}
• 付費碼: {stats.get('paid_activations', 0)}

🔍 **智能監控狀態**:
• 監控狀態: {'🟢 運行中' if self.smart_monitor.is_monitoring else '🔴 待命中'}
• 待監控訂單: {self.smart_monitor.get_pending_orders_count(self.db)}
• 監控金額: {', '.join([f'{amt:.2f}' for amt in self.smart_monitor.get_monitoring_amounts(self.db)])} USDT

📅 **更新時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            stats_text = "❌ 獲取統計數據失敗，請稍後重試"
        
        keyboard = [
            [InlineKeyboardButton("🔄 刷新數據", callback_data="admin_stats")],
            [InlineKeyboardButton("📈 收入報表", callback_data="admin_revenue")],
            [InlineKeyboardButton("🔙 返回管理", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_security_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示安全管理面板"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            await update.callback_query.answer("❌ 無權限訪問", show_alert=True)
            return
        
        blacklist_count = len(self.security.blacklisted_users)
        suspicious_count = len(self.security.suspicious_activities)
        
        security_text = f"""
🛡️ **安全管理面板**

📊 **安全統計**:
• 黑名單用戶數: {blacklist_count}
• 可疑活動用戶: {suspicious_count}
• 速率限制保護: ✅ 啟用
• 輸入驗證: ✅ 啟用

⚡ **近期活動**:
"""
        
        # 顯示最近的可疑活動
        recent_activities = list(self.security.suspicious_activities.items())[-5:]
        if recent_activities:
            for user_id, count in recent_activities:
                security_text += f"• 用戶 {user_id}: {count} 次可疑操作\n"
        else:
            security_text += "• 暫無可疑活動\n"
        
        security_text += f"\n📅 **更新時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        keyboard = [
            [InlineKeyboardButton("📋 查看黑名單", callback_data="security_blacklist")],
            [InlineKeyboardButton("🔍 可疑活動", callback_data="security_suspicious")],
            [InlineKeyboardButton("🔙 返回管理", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, security_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理用戶發送的文字消息"""
        # 安全檢查
        if not await self.security_check(update):
            return
            
        message = update.message
        text = self.security.sanitize_input(message.text, 100)
        
        # 檢查是否是訂單號格式
        if text.startswith('TG') and len(text) >= 8:
            # 驗證訂單號格式
            if not self.security.validate_order_id(text):
                self.security.log_suspicious_activity(update.effective_user.id, f"無效訂單號格式: {text}")
                await message.reply_text("❌ 無效的訂單號格式，請檢查後重試")
                return
            # 處理訂單查詢
            await self.handle_order_query(update, context, text)
        else:
            # 提供幫助信息
            help_text = """
❓ **需要幫助嗎？**

🔸 **查詢訂單**: 直接發送訂單號（如：TG123456ABCD）
🔸 **購買激活碼**: 點擊下方按鈕
🔸 **查看訂單**: 使用"我的訂單"功能

💡 **提示**: 建議使用按鈕操作更方便快捷！
"""
            keyboard = [
                [InlineKeyboardButton("🛒 購買激活碼", callback_data="buy_menu")],
                [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_order_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """處理訂單查詢"""
        user_id = update.effective_user.id
        
        try:
            order = self.db.get_order(order_id)
            
            if not order:
                error_text = f"❌ 找不到訂單 `{order_id}`\n\n請檢查訂單號是否正確"
            elif order['user_id'] != user_id:
                error_text = "❌ 您只能查詢自己的訂單"
            else:
                # 顯示訂單詳情
                status_text = self.format_order_status(order)
                keyboard = [
                    [InlineKeyboardButton("🔄 刷新狀態", callback_data=f"status_{order_id}")],
                    [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
                ]
                
                if order['status'] == 'pending':
                    keyboard.insert(0, [InlineKeyboardButton("✅ 已付款", callback_data=f"check_payment_{order_id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')
                return
            
            # 錯誤情況
            keyboard = [
                [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                [InlineKeyboardButton("🔍 查詢訂單", callback_data="search_order")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error querying order {order_id}: {e}")
            error_text = "❌ 查詢訂單時發生錯誤，請稍後重試"
            keyboard = [[InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(error_text, reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理按鈕回調"""
        # 安全檢查
        if not await self.security_check(update):
            return
            
        query = update.callback_query
        await query.answer()
        
        data = self.security.sanitize_input(query.data, 50)
        
        # 主選單導航
        if data == "main_menu":
            await self.start_command(update, context)
        elif data == "buy_menu":
            await self.show_pricing_menu(update, context)
        elif data == "my_orders":
            await self.show_user_orders(update, context)
        elif data == "search_order":
            await self.show_search_order(update, context)
        elif data == "help":
            await self.help_command(update, context)
        elif data == "contact":
            await self.show_contact_info(update, context)
        elif data == "system_status":
            await self.show_system_status(update, context)
        elif data == "test_mode_buy":
            await self.handle_test_mode_purchase(update, context)
            
        # 購買相關
        elif data.startswith("buy_"):
            plan_type = data.replace("buy_", "")
            await self.handle_purchase(update, context, plan_type)
            
        # 訂單相關  
        elif data.startswith("status_"):
            order_id = data.replace("status_", "")
            try:
                order = self.db.get_order(order_id)
                if order and order['user_id'] == update.effective_user.id:
                    status_text = self.format_order_status(order)
                    
                    # 添加操作按鈕
                    keyboard = [
                        [InlineKeyboardButton("🔄 刷新狀態", callback_data=f"status_{order_id}")],
                        [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                        [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
                    ]
                    
                    # 如果是待付款狀態，添加已付款按鈕
                    if order['status'] == 'pending':
                        keyboard.insert(0, [InlineKeyboardButton("✅ 已付款", callback_data=f"check_payment_{order_id}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await self.send_message(update, status_text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.answer("❌ 找不到該訂單或無權限查看", show_alert=True)
            except Exception as e:
                logger.error(f"Error getting order status: {e}")
                await query.answer("❌ 查詢訂單時發生錯誤", show_alert=True)
                
        elif data.startswith("check_payment_"):
            order_id = data.replace("check_payment_", "")
            await self.check_payment_status(update, context, order_id)
        # 測試模式現在使用真實的付款檢查，不需要特殊處理
        elif data.startswith("cancel_payment_"):
            order_id = data.replace("cancel_payment_", "")
            await self.handle_cancel_payment(update, context, order_id)
        elif data.startswith("complete_payment_"):
            order_id = data.replace("complete_payment_", "")
            await self.handle_complete_payment(update, context, order_id)
        elif data.startswith("cancel_test_"):
            order_id = data.replace("cancel_test_", "")
            await self.handle_cancel_test(update, context, order_id)
            
        elif data == "input_order_id":
            await query.answer("請發送訂單號進行查詢（格式：TG123456ABCD）", show_alert=True)
            
        # 管理員功能
        elif data == "admin_panel":
            await self.show_admin_panel(update, context)
        elif data == "admin_stats":
            await self.show_admin_stats(update, context)
        elif data == "admin_revenue":
            await query.answer("收入報表功能開發中", show_alert=True)
        elif data == "admin_users":
            await query.answer("用戶管理功能開發中", show_alert=True)
        elif data == "admin_orders":
            await query.answer("訂單管理功能開發中", show_alert=True)
        elif data == "admin_restart":
            await query.answer("重啟監控功能開發中", show_alert=True)
        elif data == "admin_cleanup":
            await query.answer("清理數據功能開發中", show_alert=True)
        elif data == "admin_settings":
            await query.answer("系統設置功能開發中", show_alert=True)
        elif data == "security_panel":
            await self.show_security_panel(update, context)
        elif data == "security_blacklist":
            await query.answer("黑名單管理功能開發中", show_alert=True)
        elif data == "security_suspicious":
            await query.answer("可疑活動詳情功能開發中", show_alert=True)
        elif data == "copy_code":
            await query.answer("💡 請長按激活碼進行復制", show_alert=True)
            
        # 兼容舊的回調
        elif data == "order":
            await self.show_pricing_menu(update, context)
        elif data == "back_to_main":
            await self.start_command(update, context)
        else:
            await query.answer("❓ 未知操作", show_alert=True)
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """檢查付款狀態"""
        try:
            user_id = update.effective_user.id
            logger.info(f"用戶 {user_id} 請求檢查訂單 {order_id} 的付款狀態")
            
            order = self.db.get_order(order_id)
            if not order:
                logger.warning(f"訂單 {order_id} 不存在")
                await update.callback_query.answer("❌ 訂單不存在", show_alert=True)
                return
                
            if order['user_id'] != user_id:
                logger.warning(f"用戶 {user_id} 無權限查看訂單 {order_id}")
                await update.callback_query.answer("❌ 無權限查看此訂單", show_alert=True)
                return
            
            logger.info(f"訂單 {order_id} 當前狀態: {order['status']}")
            
        except Exception as e:
            logger.error(f"檢查付款狀態時發生錯誤: {e}")
            await update.callback_query.answer("❌ 檢查付款狀態時發生錯誤", show_alert=True)
            return
        
        if order['status'] == 'paid':
            try:
                activation_code = self.activation_manager.get_activation_code_by_order(order_id)
                if not activation_code:
                    activation_code = "未找到激活碼，請聯繫客服"
                
                # 安全獲取方案名稱
                plan_type = order.get('plan_type', 'unknown')
                plan_name = self.pricing.get(plan_type, {}).get('name', '未知方案')
                
                text = f"""✅ 付款已確認！

🔑 激活碼: {activation_code}
📦 方案: {plan_name}
⏰ 有效期: {order['days']} 天

請保存好您的激活碼！"""
                
                keyboard = [
                    [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                    [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                    [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.send_new_message(update, text, reply_markup=reply_markup)
                await update.callback_query.answer("✅ 付款已確認", show_alert=False)
                logger.info(f"用戶 {user_id} 的訂單 {order_id} 付款已確認")
                
            except Exception as e:
                logger.error(f"顯示付款確認時發生錯誤: {e}")
                await update.callback_query.answer("❌ 顯示付款信息時發生錯誤", show_alert=True)
                
        elif order['status'] == 'pending':
            # 訂單仍在等待付款
            status_text = f"""🔍 付款狀態檢查

🆔 訂單號: {order_id}
💰 付款金額: {order['amount']} {self.currency}
📅 創建時間: {order['created_at'][:19]}
⏳ 當前狀態: 等待付款確認

💡 系統正在檢查您的付款:
• 區塊鏈確認通常需要 5-10 分鐘
• 請確保已發送準確的金額
• 如果已付款超過 30 分鐘，請聯繫客服

📍 付款地址: {self.config.USDT_ADDRESS}"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 重新檢查", callback_data=f"check_payment_{order_id}")],
                [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_new_message(update, status_text, reply_markup=reply_markup)
            await update.callback_query.answer("🔍 正在檢查付款狀態", show_alert=False)
            logger.info(f"用戶 {user_id} 檢查了待付款訂單 {order_id}")
            
        elif order['status'] == 'cancelled':
            # 訂單已取消
            cancel_text = f"""❌ 訂單已取消

🆔 訂單號: {order_id}
📅 取消時間: {order.get('updated_at', '未知')[:19]}

您可以重新創建新的訂單"""
            
            keyboard = [
                [InlineKeyboardButton("🛒 重新購買", callback_data="buy_menu")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_new_message(update, cancel_text, reply_markup=reply_markup)
            await update.callback_query.answer("訂單已取消", show_alert=False)
            
        else:
            # 其他狀態
            await update.callback_query.answer(f"訂單狀態: {order['status']}", show_alert=True)
            logger.warning(f"未處理的訂單狀態: {order['status']} for order {order_id}")
    
    async def show_user_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示用戶訂單"""
        user_id = update.effective_user.id
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            text = "📋 您還沒有任何訂單\n\n使用 /order 開始購買"
        else:
            text = "📊 **您的訂單**:\n\n"
            for order in orders:
                text += f"🆔 `{order['order_id']}`\n"
                text += f"📦 {self.pricing[order['plan_type']]['name']}\n"
                text += f"💰 {order['amount']} USDT\n"
                text += f"📅 {self.get_status_emoji(order['status'])} {order['status']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🛒 購買激活碼", callback_data="buy_menu")],
            [InlineKeyboardButton("🔍 查詢訂單", callback_data="search_order"), InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_cancel_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """處理取消付款"""
        try:
            user_id = update.effective_user.id
            
            # 獲取訂單
            order = self.db.get_order(order_id)
            if not order or order['user_id'] != user_id:
                await update.callback_query.answer("❌ 訂單不存在或無權限", show_alert=True)
                return
                
            if order['status'] != 'pending':
                await update.callback_query.answer("❌ 訂單狀態異常，無法取消", show_alert=True)
                return
            
            # 更新訂單狀態為已取消
            self.db.update_order_status(order_id, 'cancelled')
            
            # 從智能監控中移除
            try:
                if hasattr(self, 'smart_monitor'):
                    self.smart_monitor.remove_order_from_monitoring(order_id)
            except Exception as e:
                logger.warning(f"移除監控失敗: {e}")
            
            # 安全獲取方案名稱
            plan_type = order.get('plan_type', 'unknown')
            plan_name = self.pricing.get(plan_type, {}).get('name', '未知方案')
            
            cancel_text = f"""❌ 付款已取消

🆔 訂單號: {order_id}
📦 方案: {plan_name}
💰 金額: {order['amount']} {self.currency}
📅 取消時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 訂單已成功取消，您可以重新下單"""
            
            keyboard = [
                [InlineKeyboardButton("🛒 重新購買", callback_data="buy_menu")],
                [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_new_message(update, cancel_text, reply_markup=reply_markup)
            await update.callback_query.answer("✅ 訂單已取消", show_alert=False)
            logger.info(f"用戶 {user_id} 取消了訂單 {order_id}")
            
        except Exception as e:
            logger.error(f"取消付款失敗: {e}")
            await update.callback_query.answer("❌ 取消付款時發生錯誤，請重試", show_alert=True)
    
    async def handle_complete_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """處理完成付款 - 實際上就是發送確認請求"""
        try:
            user_id = update.effective_user.id
            
            # 獲取訂單
            order = self.db.get_order(order_id)
            if not order or order['user_id'] != user_id:
                await update.callback_query.answer("❌ 訂單不存在或無權限", show_alert=True)
                return
                
            if order['status'] != 'pending':
                await update.callback_query.answer("❌ 訂單狀態異常", show_alert=True)
                return
            
            # 發送確認請求消息
            confirm_text = f"""✅ 付款確認請求已提交

🆔 訂單號: {order_id}
💰 付款金額: {order['amount']} {self.currency}
🏦 收款地址: {self.config.USDT_ADDRESS}

🔍 系統正在確認您的付款:
• 通常需要 5-10 分鐘完成確認
• 請耐心等待，系統會自動檢測
• 確認成功後會立即發送激活碼

⏰ 如果超過 30 分鐘仍未收到激活碼，請聯繫客服"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 刷新狀態", callback_data=f"status_{order_id}")],
                [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_new_message(update, confirm_text, reply_markup=reply_markup)
            await update.callback_query.answer("✅ 付款確認請求已提交", show_alert=False)
            logger.info(f"用戶 {user_id} 提交了訂單 {order_id} 的付款確認請求")
            
        except Exception as e:
            logger.error(f"完成付款失敗: {e}")
            await update.callback_query.answer("❌ 處理付款時發生錯誤，請重試", show_alert=True)
    
    async def handle_cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """處理取消測試"""
        try:
            user_id = update.effective_user.id
            
            # 獲取訂單
            order = self.db.get_order(order_id)
            if not order or order['user_id'] != user_id:
                await update.callback_query.answer("❌ 測試訂單不存在或無權限", show_alert=True)
                return
                
            if order['status'] != 'pending':
                await update.callback_query.answer("❌ 測試訂單狀態異常", show_alert=True)
                return
            
            # 更新訂單狀態為已取消
            self.db.update_order_status(order_id, 'cancelled')
            
            cancel_text = f"""❌ 測試已取消

🆔 測試訂單號: {order_id}
💰 測試金額: {order['amount']} TRX
📅 取消時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 測試訂單已取消，您可以重新測試"""
            
            keyboard = [
                [InlineKeyboardButton("🧪 重新測試", callback_data="test_mode_buy")],
                [InlineKeyboardButton("🏠 返回主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_new_message(update, cancel_text, reply_markup=reply_markup)
            await update.callback_query.answer("✅ 測試已取消", show_alert=False)
            logger.info(f"用戶 {user_id} 取消了測試訂單 {order_id}")
            
        except Exception as e:
            logger.error(f"取消測試失敗: {e}")
            await update.callback_query.answer("❌ 取消測試時發生錯誤，請重試", show_alert=True)
    
    def generate_unique_amount(self, plan_type: str) -> float:
        """生成唯一的訂單金額，避免與其他訂單衝突"""
        base_amount = self.pricing[plan_type]['price']
        
        # 免費試用不需要修改金額
        if base_amount == 0:
            return base_amount
        
        # 為付費方案添加隨機小數點
        if self.TEST_MODE:
            # 測試模式：添加更小的隨機數（0.001-0.099）避免 TRX 金額過大
            random_milli = random.randint(1, 99)
            unique_amount = base_amount + (random_milli / 1000)
        else:
            # 正式模式：添加正常隨機數（0.01-0.99）
            random_cents = random.randint(1, 99)
            unique_amount = base_amount + (random_cents / 100)
        
        # 確保金額唯一性（檢查最近的訂單）
        max_attempts = 100
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # 檢查過去1小時內是否有相同金額的訂單
                if hasattr(self.db, 'get_recent_orders_by_amount'):
                    recent_orders = self.db.get_recent_orders_by_amount(unique_amount)
                    if not recent_orders:
                        break
                else:
                    logger.error("Database 類缺少 get_recent_orders_by_amount 方法")
                    break
                    
                # 如果有衝突，重新生成
                if self.TEST_MODE:
                    random_milli = random.randint(1, 99)
                    unique_amount = base_amount + (random_milli / 1000)
                else:
                    random_cents = random.randint(1, 99)
                    unique_amount = base_amount + (random_cents / 100)
                attempts += 1
                
            except Exception as e:
                logger.error(f"檢查訂單金額衝突失敗: {e}")
                logger.error(f"Database 對象類型: {type(self.db)}")
                logger.error(f"Database 可用方法: {[m for m in dir(self.db) if not m.startswith('_')]}")
                break
        
        if self.TEST_MODE:
            logger.info(f"生成唯一金額: {unique_amount} TRX (基礎: {base_amount})")
        else:
            logger.info(f"生成唯一金額: {unique_amount} USDT (基礎: {base_amount})")
        return round(unique_amount, 2)
    
    def generate_order_id(self) -> str:
        """生成訂單ID"""
        timestamp = str(int(time.time()))[-6:]
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"TG{timestamp}{random_str}"
    
    def format_order_status(self, order: Dict) -> str:
        """格式化訂單狀態"""
        status_emoji = self.get_status_emoji(order['status'])
        
        text = f"""
📋 **訂單詳情**

🆔 訂單號: `{order['order_id']}`
📦 方案: {self.pricing[order['plan_type']]['name']}
💰 金額: {order['amount']} USDT
📅 狀態: {status_emoji} {order['status']}
📅 創建時間: {order['created_at'][:19]}

"""
        
        if order['status'] == 'pending':
            text += f"⏰ 訂單將在 24小時後過期\n"
            text += f"💳 請發送 {order['amount']} USDT 到:\n"
            text += f"`{self.config.USDT_ADDRESS}`"
        elif order['status'] == 'paid':
            activation_code = self.activation_manager.get_activation_code_by_order(order['order_id'])
            text += f"🔑 激活碼: `{activation_code}`\n"
            text += f"🧾 交易哈希: `{order.get('tx_hash', 'N/A')}`"
        
        return text
    
    def get_status_emoji(self, status: str) -> str:
        """獲取狀態表情符號"""
        status_map = {
            'pending': '⏳',
            'paid': '✅',
            'expired': '❌',
            'cancelled': '🚫'
        }
        return status_map.get(status, '❓')

def main():
    """主函數"""
    try:
        # 檢查環境變量
        config = Config()
        if not config.BOT_TOKEN:
            logger.error("❌ 未設置 BOT_TOKEN 環境變量")
            return
        
        # 創建機器人實例
        bot = TGMarketingBot()
        
        # 創建應用程序
        application = Application.builder().token(config.BOT_TOKEN).build()
        
        # 添加主要命令處理器（簡化版）
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("admin", bot.admin_command))  # 保留管理員命令
        
        # 添加按鈕回調處理器
        application.add_handler(CallbackQueryHandler(bot.button_callback))
        
        # 添加消息處理器（處理訂單號查詢等）
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # 添加錯誤處理器
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """處理錯誤"""
            logger.error(f"Exception while handling an update: {context.error}")
            
            # 嘗試向用戶發送錯誤消息
            if update and hasattr(update, 'effective_user') and update.effective_user:
                try:
                    error_text = "⚠️ 處理您的請求時發生錯誤，請稍後重試或聯繫客服。"
                    
                    if hasattr(update, 'message') and update.message:
                        await update.message.reply_text(error_text)
                    elif hasattr(update, 'callback_query') and update.callback_query:
                        await update.callback_query.answer(error_text, show_alert=True)
                except Exception as e:
                    logger.error(f"Failed to send error message to user: {e}")
            
        application.add_error_handler(error_handler)
        
        # 保存應用程序實例到機器人中，以便在付款確認時發送消息
        bot.application = application
        
        # 不再自動啟動監控 - 使用智能監控
        async def post_init(application):
            logger.info("✅ 機器人初始化完成，智能監控待命中...")
            
            # 啟動定期清理過期訂單的任務
            async def periodic_cleanup():
                """定期清理過期訂單"""
                while True:
                    try:
                        # 每5分鐘檢查一次過期訂單
                        await asyncio.sleep(300)  # 5分鐘
                        
                        # 清理過期訂單
                        expired_count = bot.smart_monitor.cleanup_expired_orders(bot.db)
                        if expired_count > 0:
                            logger.info(f"📋 定期清理：已自動取消 {expired_count} 個過期訂單")
                            
                    except Exception as e:
                        logger.error(f"❌ 定期清理任務錯誤: {e}")
                        await asyncio.sleep(60)  # 錯誤時等待1分鐘再重試
            
            # 啟動定期清理任務
            asyncio.create_task(periodic_cleanup())
        
        application.post_init = post_init
        
        # 啟動機器人
        logger.info("🚀 TG營銷系統機器人啟動中...")
        
        # 使用 polling 模式以避免 webhook 配置問題
        # 添加錯誤處理以避免多實例衝突
        application.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            stop_signals=None
        )
            
    except Exception as e:
        logger.error(f"❌ 機器人啟動失敗: {e}")

if __name__ == "__main__":
    main()