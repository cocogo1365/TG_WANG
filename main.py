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
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)

from config import Config
from database import Database
from tron_monitor import TronMonitor
from activation_codes import ActivationCodeManager

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

class TGMarketingBot:
    """TG營銷系統機器人主類"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.tron_monitor = TronMonitor()
        self.activation_manager = ActivationCodeManager()
        
        # 價格配置
        self.pricing = {
            'trial': {'days': 2, 'price': 0, 'name': '免費試用'},
            'weekly': {'days': 7, 'price': 20.0, 'name': '一週方案'},
            'monthly': {'days': 30, 'price': 70.0, 'name': '一個月方案'}
        }
        
        # 監控將在應用程序啟動後開始
    
    async def start_monitoring(self):
        """啟動交易監控"""
        try:
            await self.tron_monitor.start_monitoring(self.handle_payment_confirmed)
            logger.info("✅ TRON交易監控已啟動")
        except Exception as e:
            logger.error(f"❌ 啟動交易監控失敗: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /start 命令"""
        user = update.effective_user
        user_id = user.id
        
        # 記錄用戶
        self.db.add_user(user_id, user.username, user.first_name)
        
        # 檢查是否已有試用記錄
        trial_used = self.db.has_used_trial(user_id)
        
        welcome_text = f"""
🎯 歡迎使用 TG營銷系統 🎯

你好 {user.first_name}！

📋 **功能介紹**：
• 多賬戶管理
• 智能群組邀請
• 批量消息發送
• 數據採集和分析
• 防封號保護

💰 **價格方案**：
• 🆓 免費試用：2天 (每個TG帳戶限用一次)
• 📅 一週方案：20 USDT (7天)
• 📅 一個月方案：70 USDT (30天)

⚡ **使用 USDT (TRC-20) 支付**
💳 自動發放激活碼

使用 /order 開始購買
使用 /help 查看幫助
"""
        
        if trial_used:
            welcome_text += "\n⚠️ 您已使用過免費試用，請選擇付費方案"
        else:
            welcome_text += "\n🎁 您可以免費試用2天！"
        
        keyboard = [
            [InlineKeyboardButton("🛒 立即購買", callback_data="order")],
            [InlineKeyboardButton("❓ 幫助", callback_data="help")],
            [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def order_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /order 命令"""
        await self.show_pricing_menu(update, context)
    
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
        text += "📅 **一週方案** - 20 USDT\n"
        text += "   7天完整使用權限\n"
        text += "   所有功能無限制\n\n"
        keyboard.append([InlineKeyboardButton("💳 購買一週 (20 USDT)", callback_data="buy_weekly")])
        
        text += "📅 **一個月方案** - 70 USDT\n"
        text += "   30天完整使用權限\n"
        text += "   所有功能無限制\n"
        text += "   最優價格比例\n\n"
        keyboard.append([InlineKeyboardButton("💳 購買一個月 (70 USDT)", callback_data="buy_monthly")])
        
        text += "💡 使用 USDT (TRC-20) 支付，自動發放激活碼"
        
        keyboard.append([InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str):
        """處理購買請求"""
        user_id = update.effective_user.id
        user = update.effective_user
        
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
            await update.callback_query.edit_message_text(text, parse_mode='Markdown')
            
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
                'amount': plan_info['price'],
                'days': plan_info['days'],
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            self.db.create_order(order_data)
            
            # 顯示付款信息
            text = f"""
💳 **訂單詳情**

📋 訂單號: `{order_id}`
📦 方案: {plan_info['name']}
💰 金額: {plan_info['price']} USDT (TRC-20)
⏰ 有效期: {plan_info['days']} 天

💳 **付款信息**:
🏦 收款地址: `{self.config.USDT_ADDRESS}`
💰 付款金額: {plan_info['price']} USDT
🌐 網絡: TRON (TRC-20)

⚠️ **重要提醒**:
• 請準確發送 {plan_info['price']} USDT
• 使用 TRC-20 網絡
• 付款後5-10分鐘內自動發放激活碼
• 訂單有效期24小時

🔍 使用 /status {order_id} 查詢訂單狀態
"""
            
            keyboard = [
                [InlineKeyboardButton("✅ 已付款", callback_data=f"check_payment_{order_id}")],
                [InlineKeyboardButton("📊 查詢狀態", callback_data=f"status_{order_id}")],
                [InlineKeyboardButton("🔙 返回選單", callback_data="order")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
            
            # 發送激活碼給用戶
            text = f"""
🎉 **付款確認！激活碼已生成**

💳 訂單號: `{order['order_id']}`
🔑 激活碼: `{activation_code}`
⏰ 有效期: {order['days']} 天
🧾 交易哈希: `{tx_hash}`

📝 **使用方法**:
1. 下載TG營銷系統軟件
2. 在軟件中輸入激活碼
3. 開始使用所有功能

感謝您的購買！🙏
"""
            
            # 發送消息給用戶
            application = context.application if hasattr(self, 'context') else None
            if application:
                await application.bot.send_message(
                    chat_id=order['user_id'],
                    text=text,
                    parse_mode='Markdown'
                )
            
            logger.info(f"✅ 訂單 {order['order_id']} 處理完成，激活碼: {activation_code}")
            
        except Exception as e:
            logger.error(f"❌ 處理付款確認失敗: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /status 命令"""
        args = context.args
        user_id = update.effective_user.id
        
        if args:
            # 查詢特定訂單
            order_id = args[0]
            order = self.db.get_order(order_id)
            
            if not order or order['user_id'] != user_id:
                await update.message.reply_text("❌ 找不到該訂單或無權限查看")
                return
            
            status_text = self.format_order_status(order)
            await update.message.reply_text(status_text, parse_mode='Markdown')
        else:
            # 顯示用戶所有訂單
            orders = self.db.get_user_orders(user_id)
            
            if not orders:
                await update.message.reply_text("📋 您還沒有任何訂單")
                return
            
            text = "📊 **您的訂單**:\n\n"
            for order in orders:
                text += f"🆔 {order['order_id']}\n"
                text += f"📦 {self.pricing[order['plan_type']]['name']}\n"
                text += f"💰 {order['amount']} USDT\n"
                text += f"📅 {order['status']}\n\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /help 命令"""
        help_text = """
📖 **TG營銷系統使用幫助**

🤖 **機器人命令**:
• /start - 開始使用
• /order - 購買激活碼
• /status - 查詢訂單狀態
• /help - 顯示幫助

💰 **價格方案**:
• 🆓 免費試用: 2天 (每帳戶限用一次)
• 📅 一週方案: 20 USDT
• 📅 一個月方案: 70 USDT

💳 **付款方式**:
• 支持 USDT (TRC-20)
• 自動確認付款
• 即時發放激活碼

📝 **軟件功能**:
• 多賬戶管理
• 智能群組邀請
• 批量消息發送
• 數據採集分析
• 防封號保護

❓ **常見問題**:
• 付款後多久收到激活碼？通常5-10分鐘
• 激活碼可以重複使用嗎？每個激活碼只能用一次
• 試用版有功能限制嗎？無限制，僅時間限制

📞 **客服支持**: @your_support_username
"""
        if update.message:
            await update.message.reply_text(help_text, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /admin 命令"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            await update.message.reply_text("❌ 無權限訪問管理功能")
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
            [InlineKeyboardButton("📊 詳細統計", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 用戶管理", callback_data="admin_users")],
            [InlineKeyboardButton("🔄 重啟監控", callback_data="admin_restart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理按鈕回調"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "order":
            await self.show_pricing_menu(update, context)
        elif data.startswith("buy_"):
            plan_type = data.replace("buy_", "")
            await self.handle_purchase(update, context, plan_type)
        elif data.startswith("status_"):
            order_id = data.replace("status_", "")
            order = self.db.get_order(order_id)
            if order:
                status_text = self.format_order_status(order)
                await query.edit_message_text(status_text, parse_mode='Markdown')
        elif data.startswith("check_payment_"):
            order_id = data.replace("check_payment_", "")
            await self.check_payment_status(update, context, order_id)
        elif data == "help":
            await self.help_command(update, context)
        elif data == "my_orders":
            await self.show_user_orders(update, context)
        elif data == "back_to_main":
            await self.start_command(update, context)
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """檢查付款狀態"""
        order = self.db.get_order(order_id)
        if not order:
            await update.callback_query.answer("❌ 訂單不存在", show_alert=True)
            return
        
        if order['status'] == 'paid':
            activation_code = self.activation_manager.get_activation_code_by_order(order_id)
            text = f"""
✅ **付款已確認！**

🔑 激活碼: `{activation_code}`
📦 方案: {self.pricing[order['plan_type']]['name']}
⏰ 有效期: {order['days']} 天

請保存好您的激活碼！
"""
            await update.callback_query.edit_message_text(text, parse_mode='Markdown')
        else:
            await update.callback_query.answer("💰 正在檢查付款狀態，請稍候...", show_alert=True)
    
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
        
        keyboard = [[InlineKeyboardButton("🔙 返回主選單", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
        
        # 添加命令處理器
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("order", bot.order_command))
        application.add_handler(CommandHandler("status", bot.status_command))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(CommandHandler("admin", bot.admin_command))
        
        # 添加按鈕回調處理器
        application.add_handler(CallbackQueryHandler(bot.button_callback))
        
        # 保存應用程序實例到機器人中，以便在付款確認時發送消息
        bot.application = application
        
        # 啟動監控任務
        async def post_init(application):
            asyncio.create_task(bot.start_monitoring())
        
        application.post_init = post_init
        
        # 啟動機器人
        logger.info("🚀 TG營銷系統機器人啟動中...")
        
        # 使用 polling 模式以避免 webhook 配置問題
        application.run_polling(drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"❌ 機器人啟動失敗: {e}")

if __name__ == "__main__":
    main()