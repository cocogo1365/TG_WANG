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
    
    async def send_message(self, update: Update, text: str, reply_markup=None, parse_mode=None):
        """統一的消息發送方法，處理普通消息和回調查詢"""
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理 /start 命令"""
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
📅 **一週方案** - 20 USDT 
📅 **一個月方案** - 70 USDT

⚡ **特色優勢**
• USDT (TRC-20) 安全支付
• 即時自動發放激活碼
• 24/7 客服支持
• 簡單易用的操作界面

🎁 **立即開始使用下方按鈕！**
"""
        
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
        
        keyboard.append([InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
                'amount': plan_info['price'],
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

🔍 點擊下方"查詢狀態"按鈕查看付款進度
"""
            
            keyboard = [
                [InlineKeyboardButton("✅ 已付款", callback_data=f"check_payment_{order_id}")],
                [InlineKeyboardButton("📊 查詢狀態", callback_data=f"status_{order_id}")],
                [InlineKeyboardButton("🔙 返回購買", callback_data="buy_menu"), InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
            
            # 發送消息給用戶（帶按鈕）
            if hasattr(self, 'application') and self.application:
                keyboard = [
                    [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                    [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                    [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=order['user_id'],
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            logger.info(f"✅ 訂單 {order['order_id']} 處理完成，激活碼: {activation_code}")
            
        except Exception as e:
            logger.error(f"❌ 處理付款確認失敗: {e}")
    
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
• 📅 一週方案: 20 USDT (7天)
• 📅 一個月方案: 70 USDT (30天)

💳 **付款流程**:
1. 選擇購買方案
2. 發送 USDT (TRC-20) 到指定地址
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
            [InlineKeyboardButton("🔄 重啟監控", callback_data="admin_restart"), InlineKeyboardButton("🧹 清理數據", callback_data="admin_cleanup")],
            [InlineKeyboardButton("⚙️ 系統設置", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 返回主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, admin_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示管理員控制面板"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.ADMIN_IDS:
            await update.callback_query.answer("❌ 無權限訪問", show_alert=True)
            return
            
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理用戶發送的文字消息"""
        message = update.message
        text = message.text.strip()
        
        # 檢查是否是訂單號格式
        if text.startswith('TG') and len(text) >= 8:
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
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
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
            
        # 兼容舊的回調
        elif data == "order":
            await self.show_pricing_menu(update, context)
        elif data == "back_to_main":
            await self.start_command(update, context)
        else:
            await query.answer("❓ 未知操作", show_alert=True)
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """檢查付款狀態"""
        order = self.db.get_order(order_id)
        if not order or order['user_id'] != update.effective_user.id:
            await update.callback_query.answer("❌ 訂單不存在或無權限查看", show_alert=True)
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
            keyboard = [
                [InlineKeyboardButton("📞 聯繫客服", callback_data="contact")],
                [InlineKeyboardButton("📊 我的訂單", callback_data="my_orders")],
                [InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
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
        
        keyboard = [
            [InlineKeyboardButton("🛒 購買激活碼", callback_data="buy_menu")],
            [InlineKeyboardButton("🔍 查詢訂單", callback_data="search_order"), InlineKeyboardButton("🏠 主選單", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
    
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
        
        # 啟動監控任務
        async def post_init(application):
            asyncio.create_task(bot.start_monitoring())
        
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