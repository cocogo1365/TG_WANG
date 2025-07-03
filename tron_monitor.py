#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRON 交易監控模塊
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import aiohttp
from config import Config
from database import Database

logger = logging.getLogger(__name__)

class TronMonitor:
    """TRON 區塊鏈交易監控器"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.is_monitoring = False
        self.last_checked_block = 0
        # 檢查是否為測試模式
        self.test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
    async def start_monitoring(self, payment_callback: Callable):
        """開始監控交易"""
        self.is_monitoring = True
        self.payment_callback = payment_callback
        
        # 獲取當前區塊高度
        self.last_checked_block = await self.get_latest_block_number()
        currency = "TRX" if self.test_mode else "USDT"
        logger.info(f"🔍 開始監控 {currency} 交易，從區塊 {self.last_checked_block} 開始")
        
        while self.is_monitoring:
            try:
                await self.check_new_transactions()
                await asyncio.sleep(self.config.MONITORING_INTERVAL)
            except Exception as e:
                logger.error(f"❌ 監控交易時發生錯誤: {e}")
                await asyncio.sleep(60)  # 錯誤時等待更長時間
    
    def stop_monitoring(self):
        """停止監控"""
        self.is_monitoring = False
        logger.info("⏹️ 停止 TRON 交易監控")
    
    async def get_latest_block_number(self) -> int:
        """獲取最新區塊號"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.TRONGRID_API_URL}/wallet/getnowblock"
                headers = self.config.get_trongrid_headers()
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('block_header', {}).get('raw_data', {}).get('number', 0)
                    else:
                        logger.error(f"❌ 獲取最新區塊失敗: HTTP {response.status}")
                        return 0
        except Exception as e:
            logger.error(f"❌ 獲取最新區塊時發生錯誤: {e}")
            return 0
    
    async def check_new_transactions(self):
        """檢查新交易"""
        try:
            current_block = await self.get_latest_block_number()
            if current_block <= self.last_checked_block:
                return
            
            # 檢查新區塊中的交易
            for block_num in range(self.last_checked_block + 1, current_block + 1):
                await self.check_block_transactions(block_num)
            
            self.last_checked_block = current_block
            
        except Exception as e:
            logger.error(f"❌ 檢查新交易時發生錯誤: {e}")
    
    async def check_block_transactions(self, block_number: int):
        """檢查指定區塊的交易"""
        try:
            # 獲取區塊信息
            block_data = await self.get_block_by_number(block_number)
            if not block_data:
                return
            
            transactions = block_data.get('transactions', [])
            
            for tx in transactions:
                await self.process_transaction(tx)
                
        except Exception as e:
            logger.error(f"❌ 檢查區塊 {block_number} 交易時發生錯誤: {e}")
    
    async def get_block_by_number(self, block_number: int) -> Optional[Dict]:
        """根據區塊號獲取區塊信息"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.TRONGRID_API_URL}/wallet/getblockbynum"
                headers = self.config.get_trongrid_headers()
                data = {"num": block_number}
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"⚠️ 獲取區塊 {block_number} 失敗: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ 獲取區塊 {block_number} 時發生錯誤: {e}")
            return None
    
    async def process_transaction(self, transaction: Dict):
        """處理單個交易"""
        try:
            tx_id = transaction.get('txID')
            if not tx_id:
                return
            
            # 檢查是否已處理過此交易
            if self.db.transaction_exists(tx_id):
                return
            
            # 檢查交易類型
            raw_data = transaction.get('raw_data', {})
            contracts = raw_data.get('contract', [])
            
            for contract in contracts:
                if self.test_mode and contract.get('type') == 'TransferContract':
                    # 測試模式：監控原生 TRX 轉賬
                    await self.process_trx_transaction(tx_id, contract, transaction)
                elif not self.test_mode and contract.get('type') == 'TriggerSmartContract':
                    # 生產模式：監控 TRC-20 (USDT) 轉賬
                    await self.process_trc20_transaction(tx_id, contract, transaction)
            
        except Exception as e:
            logger.error(f"❌ 處理交易時發生錯誤: {e}")
    
    async def process_trx_transaction(self, tx_id: str, contract: Dict, full_transaction: Dict):
        """處理原生 TRX 轉賬交易（測試模式）"""
        try:
            parameter = contract.get('parameter', {})
            value = parameter.get('value', {})
            
            # 獲取接收地址和金額
            to_address = value.get('to_address')
            amount_sun = value.get('amount', 0)  # TRX 以 sun 為單位 (1 TRX = 1,000,000 sun)
            
            if not to_address:
                return
            
            # 轉換地址格式（從 hex 到 base58）
            to_address_base58 = await self.hex_to_base58(to_address)
            
            # 檢查是否轉給我們的地址
            if to_address_base58 != self.config.USDT_ADDRESS:
                return
            
            # 轉換金額（從 sun 到 TRX）
            amount_trx = amount_sun / 1_000_000
            
            # 獲取交易詳情和確認狀態
            tx_info = await self.get_transaction_info(tx_id)
            if not tx_info:
                return
            
            # 檢查交易是否成功
            if tx_info.get('receipt', {}).get('result') != 'SUCCESS':
                logger.warning(f"⚠️ TRX 交易 {tx_id} 執行失敗")
                return
            
            # 檢查確認數
            current_block = await self.get_latest_block_number()
            tx_block = tx_info.get('blockNumber', 0)
            confirmations = current_block - tx_block
            
            if confirmations < self.config.CONFIRMATION_BLOCKS:
                logger.info(f"⏳ TRX 交易 {tx_id} 確認數不足: {confirmations}/{self.config.CONFIRMATION_BLOCKS}")
                return
            
            # 獲取發送方地址
            from_address = value.get('owner_address')
            from_address_base58 = await self.hex_to_base58(from_address) if from_address else ""
            
            # 記錄交易
            transaction_data = {
                'tx_hash': tx_id,
                'from_address': from_address_base58,
                'to_address': to_address_base58,
                'amount': amount_trx,
                'currency': 'TRX',
                'block_number': tx_block,
                'confirmations': confirmations,
                'timestamp': datetime.now().isoformat(),
                'processed': True
            }
            
            self.db.save_transaction(tx_id, transaction_data)
            
            logger.info(f"✅ 檢測到 TRX 轉賬: {amount_trx} TRX 到 {to_address_base58}")
            logger.info(f"📋 交易哈希: {tx_id}")
            
            # 調用付款回調
            if self.payment_callback:
                await self.payment_callback(transaction_data)
            
        except Exception as e:
            logger.error(f"❌ 處理 TRX 交易時發生錯誤: {e}")
    
    async def process_trc20_transaction(self, tx_id: str, contract: Dict, full_transaction: Dict):
        """處理 TRC-20 轉賬交易"""
        try:
            parameter = contract.get('parameter', {})
            value = parameter.get('value', {})
            
            # 檢查合約地址
            contract_address = value.get('contract_address')
            if not contract_address:
                return
            
            # 轉換地址格式
            contract_address_base58 = await self.hex_to_base58(contract_address)
            if contract_address_base58 != self.config.USDT_CONTRACT:
                return
            
            # 解析轉賬數據
            data = value.get('data', '')
            if not data or len(data) < 136:  # transfer方法調用的最小長度
                return
            
            # 檢查是否是 transfer 方法 (方法ID: a9059cbb)
            method_id = data[:8]
            if method_id != 'a9059cbb':
                return
            
            # 解析接收地址和金額
            to_address_hex = data[32:72]  # 跳過方法ID和填充
            amount_hex = data[72:136]
            
            # 轉換地址
            to_address = await self.hex_to_base58('41' + to_address_hex)
            
            # 檢查是否轉給我們的地址
            if to_address != self.config.USDT_ADDRESS:
                return
            
            # 轉換金額 (USDT 有 6 位小數)
            amount_wei = int(amount_hex, 16)
            amount_usdt = amount_wei / 1_000_000
            
            # 獲取交易詳情和確認狀態
            tx_info = await self.get_transaction_info(tx_id)
            if not tx_info:
                return
            
            # 檢查交易是否成功
            if tx_info.get('receipt', {}).get('result') != 'SUCCESS':
                logger.warning(f"⚠️ 交易 {tx_id} 執行失敗")
                return
            
            # 檢查確認數
            current_block = await self.get_latest_block_number()
            tx_block = tx_info.get('blockNumber', 0)
            confirmations = current_block - tx_block
            
            if confirmations < self.config.CONFIRMATION_BLOCKS:
                logger.info(f"⏳ 交易 {tx_id} 確認數不足: {confirmations}/{self.config.CONFIRMATION_BLOCKS}")
                return
            
            # 記錄交易
            transaction_data = {
                'tx_hash': tx_id,
                'from_address': await self.hex_to_base58('41' + data[32:72]),  # 發送方地址
                'to_address': to_address,
                'amount': amount_usdt,
                'currency': 'USDT',
                'block_number': tx_block,
                'confirmations': confirmations,
                'timestamp': datetime.now().isoformat(),
                'processed': True
            }
            
            self.db.save_transaction(tx_id, transaction_data)
            
            logger.info(f"✅ 檢測到 USDT 轉賬: {amount_usdt} USDT 到 {to_address}")
            logger.info(f"📋 交易哈希: {tx_id}")
            
            # 調用付款回調
            if self.payment_callback:
                await self.payment_callback(transaction_data)
            
        except Exception as e:
            logger.error(f"❌ 處理 TRC-20 交易時發生錯誤: {e}")
    
    async def get_transaction_info(self, tx_id: str) -> Optional[Dict]:
        """獲取交易詳情"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.TRONGRID_API_URL}/wallet/gettransactioninfobyid"
                headers = self.config.get_trongrid_headers()
                data = {"value": tx_id}
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"⚠️ 獲取交易 {tx_id} 詳情失敗: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"❌ 獲取交易 {tx_id} 詳情時發生錯誤: {e}")
            return None
    
    async def hex_to_base58(self, hex_address: str) -> str:
        """將十六進制地址轉換為 Base58 地址"""
        try:
            # 這是一個簡化的實現，實際項目中建議使用專門的庫
            # 如 tronpy 或 pytron
            
            # 移除 0x 前綴
            if hex_address.startswith('0x'):
                hex_address = hex_address[2:]
            
            # 轉換為字節
            addr_bytes = bytes.fromhex(hex_address)
            
            # 這裡應該實現完整的 Base58Check 編碼
            # 為了簡化，我們返回一個占位符
            # 在實際部署時，請使用 tronpy 庫進行正確的地址轉換
            
            return "T" + hex_address  # 占位符實現
            
        except Exception as e:
            logger.error(f"❌ 地址轉換錯誤: {e}")
            return ""
    
    async def get_account_transactions(self, limit: int = 20) -> List[Dict]:
        """獲取賬戶交易記錄"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.TRONGRID_API_URL}/v1/accounts/{self.config.USDT_ADDRESS}/transactions/trc20"
                headers = self.config.get_trongrid_headers()
                params = {
                    'limit': limit,
                    'contract_address': self.config.USDT_CONTRACT
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        logger.error(f"❌ 獲取賬戶交易失敗: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.error(f"❌ 獲取賬戶交易時發生錯誤: {e}")
            return []
    
    async def get_trx_transactions(self, limit: int = 20) -> List[Dict]:
        """獲取 TRX 交易記錄（測試模式）"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.TRONGRID_API_URL}/v1/accounts/{self.config.USDT_ADDRESS}/transactions"
                headers = self.config.get_trongrid_headers()
                params = {
                    'limit': limit,
                    'only_confirmed': True,
                    'only_to': True  # 只獲取轉入交易
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 過濾出 TRX 轉賬交易
                        trx_transactions = []
                        for tx in data.get('data', []):
                            # 檢查是否是 TRX 轉賬
                            for contract in tx.get('raw_data', {}).get('contract', []):
                                if contract.get('type') == 'TransferContract':
                                    trx_transactions.append({
                                        'transaction_id': tx.get('txID'),
                                        'block_timestamp': tx.get('block_timestamp'),
                                        'from': contract.get('parameter', {}).get('value', {}).get('owner_address'),
                                        'to': contract.get('parameter', {}).get('value', {}).get('to_address'),
                                        'value': contract.get('parameter', {}).get('value', {}).get('amount', 0)
                                    })
                        return trx_transactions
                    else:
                        logger.error(f"❌ 獲取 TRX 交易失敗: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.error(f"❌ 獲取 TRX 交易時發生錯誤: {e}")
            return []
    
    async def verify_payment(self, amount: float, max_age_minutes: int = 30) -> Optional[Dict]:
        """驗證指定金額的付款"""
        try:
            if self.test_mode:
                # 測試模式：檢查 TRX 交易
                return await self.verify_trx_payment(amount, max_age_minutes)
            else:
                # 生產模式：檢查 USDT 交易
                return await self.verify_usdt_payment(amount, max_age_minutes)
            
        except Exception as e:
            logger.error(f"❌ 驗證付款時發生錯誤: {e}")
            return None
    
    async def verify_trx_payment(self, amount: float, max_age_minutes: int = 30) -> Optional[Dict]:
        """驗證 TRX 付款（測試模式）"""
        try:
            # 獲取 TRX 交易記錄
            transactions = await self.get_trx_transactions(50)
            
            current_time = time.time() * 1000  # 轉換為毫秒
            max_age_ms = max_age_minutes * 60 * 1000
            
            for tx in transactions:
                # 檢查交易時間
                tx_time = tx.get('block_timestamp', 0)
                if current_time - tx_time > max_age_ms:
                    continue
                
                # 檢查交易方向（收款）
                if tx.get('to') != self.config.USDT_ADDRESS:
                    continue
                
                # 檢查金額（TRX 以 sun 為單位）
                tx_amount = float(tx.get('value', 0)) / 1_000_000  # 轉換為 TRX
                if abs(tx_amount - amount) < 0.001:  # 允許小額誤差
                    return {
                        'tx_hash': tx.get('transaction_id'),
                        'amount': tx_amount,
                        'currency': 'TRX',
                        'from_address': tx.get('from'),
                        'timestamp': tx_time,
                        'confirmations': 'confirmed'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 驗證 TRX 付款時發生錯誤: {e}")
            return None
    
    async def verify_usdt_payment(self, amount: float, max_age_minutes: int = 30) -> Optional[Dict]:
        """驗證 USDT 付款（生產模式）"""
        try:
            transactions = await self.get_account_transactions(50)
            
            current_time = time.time() * 1000  # 轉換為毫秒
            max_age_ms = max_age_minutes * 60 * 1000
            
            for tx in transactions:
                # 檢查交易時間
                tx_time = tx.get('block_timestamp', 0)
                if current_time - tx_time > max_age_ms:
                    continue
                
                # 檢查交易方向（收款）
                if tx.get('to') != self.config.USDT_ADDRESS:
                    continue
                
                # 檢查金額
                tx_amount = float(tx.get('value', 0)) / 1_000_000  # 轉換為 USDT
                if abs(tx_amount - amount) < 0.01:  # 允許小額誤差
                    return {
                        'tx_hash': tx.get('transaction_id'),
                        'amount': tx_amount,
                        'currency': 'USDT',
                        'from_address': tx.get('from'),
                        'timestamp': tx_time,
                        'confirmations': 'confirmed'  # TronGrid API 返回的交易都是已確認的
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 驗證 USDT 付款時發生錯誤: {e}")
            return None