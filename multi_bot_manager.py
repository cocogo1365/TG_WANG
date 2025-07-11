#!/usr/bin/env python3
"""
TG旺多機器人管理系統
支持多個TG機器人同時運行，代理商專屬機器人分配
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram.ext import Application
import subprocess
import threading
import time

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiBotManager:
    """多機器人管理器"""
    
    def __init__(self):
        self.bots = {}  # 儲存所有機器人實例
        self.bot_configs = {}  # 機器人配置
        self.agent_bot_mapping = {}  # 代理商-機器人映射
        self.running_processes = {}  # 運行中的進程
        
        # 從環境變量和配置文件載入機器人
        self.load_bot_configurations()
    
    def load_bot_configurations(self):
        """載入機器人配置"""
        try:
            # 主機器人配置
            main_bot_token = os.getenv('BOT_TOKEN')
            if main_bot_token:
                self.bot_configs['main'] = {
                    'token': main_bot_token,
                    'name': 'TG旺主機器人',
                    'agent_id': None,  # 主機器人不屬於特定代理
                    'database_file': 'bot_database.json',
                    'admin_ids': os.getenv('ADMIN_IDS', '').split(','),
                    'usdt_address': os.getenv('USDT_ADDRESS'),
                    'api_key': os.getenv('TRONGRID_API_KEY')
                }
            
            # 代理商機器人配置
            self.load_agent_bots()
            
            logger.info(f"📋 載入 {len(self.bot_configs)} 個機器人配置")
            
        except Exception as e:
            logger.error(f"載入機器人配置失敗: {e}")
    
    def load_agent_bots(self):
        """載入代理商機器人配置"""
        try:
            # 從環境變量載入代理商機器人
            for i in range(1, 21):  # 支持最多20個代理商機器人
                bot_token = os.getenv(f'AGENT_BOT_TOKEN_{i}')
                agent_id = os.getenv(f'AGENT_ID_{i}')
                
                if bot_token and agent_id:
                    bot_id = f'agent_{agent_id}'
                    self.bot_configs[bot_id] = {
                        'token': bot_token,
                        'name': f'代理商{agent_id}專屬機器人',
                        'agent_id': agent_id,
                        'database_file': f'bot_database_agent_{agent_id}.json',
                        'admin_ids': [agent_id],  # 代理商作為管理員
                        'usdt_address': os.getenv(f'AGENT_USDT_ADDRESS_{i}'),
                        'api_key': os.getenv('TRONGRID_API_KEY')
                    }
                    
                    # 建立代理商-機器人映射
                    self.agent_bot_mapping[agent_id] = bot_id
            
            # 從配置文件載入（可選）
            if os.path.exists('agent_bots_config.json'):
                with open('agent_bots_config.json', 'r', encoding='utf-8') as f:
                    agent_configs = json.load(f)
                    
                for agent_id, config in agent_configs.items():
                    bot_id = f'agent_{agent_id}'
                    self.bot_configs[bot_id] = {
                        'token': config['bot_token'],
                        'name': config.get('name', f'代理商{agent_id}機器人'),
                        'agent_id': agent_id,
                        'database_file': f'bot_database_agent_{agent_id}.json',
                        'admin_ids': config.get('admin_ids', [agent_id]),
                        'usdt_address': config.get('usdt_address'),
                        'api_key': config.get('api_key', os.getenv('TRONGRID_API_KEY'))
                    }
                    self.agent_bot_mapping[agent_id] = bot_id
                    
        except Exception as e:
            logger.error(f"載入代理商機器人配置失敗: {e}")
    
    def start_bot(self, bot_id: str):
        """啟動單個機器人"""
        if bot_id not in self.bot_configs:
            logger.error(f"機器人 {bot_id} 配置不存在")
            return False
        
        try:
            config = self.bot_configs[bot_id]
            
            # 為每個機器人創建環境變量
            env = os.environ.copy()
            env.update({
                'BOT_TOKEN': config['token'],
                'ADMIN_IDS': ','.join(str(id) for id in config['admin_ids']),
                'DB_PATH': config['database_file'],
                'USDT_ADDRESS': config['usdt_address'] or '',
                'TRONGRID_API_KEY': config['api_key'] or '',
                'BOT_NAME': config['name'],
                'AGENT_ID': config['agent_id'] or '',
                'TEST_MODE': os.getenv('TEST_MODE', 'true')
            })
            
            # 啟動機器人進程
            process = subprocess.Popen(
                ['python', 'main.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            self.running_processes[bot_id] = {
                'process': process,
                'config': config,
                'started_at': datetime.now()
            }
            
            logger.info(f"✅ 機器人 {config['name']} 已啟動 (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"啟動機器人 {bot_id} 失敗: {e}")
            return False
    
    def stop_bot(self, bot_id: str):
        """停止單個機器人"""
        if bot_id in self.running_processes:
            try:
                process_info = self.running_processes[bot_id]
                process = process_info['process']
                
                process.terminate()
                process.wait(timeout=10)
                
                del self.running_processes[bot_id]
                logger.info(f"🛑 機器人 {bot_id} 已停止")
                return True
                
            except Exception as e:
                logger.error(f"停止機器人 {bot_id} 失敗: {e}")
                return False
        
        return False
    
    def start_all_bots(self):
        """啟動所有機器人"""
        logger.info("🚀 啟動所有機器人...")
        
        for bot_id in self.bot_configs:
            self.start_bot(bot_id)
            time.sleep(2)  # 間隔啟動避免衝突
    
    def stop_all_bots(self):
        """停止所有機器人"""
        logger.info("🛑 停止所有機器人...")
        
        for bot_id in list(self.running_processes.keys()):
            self.stop_bot(bot_id)
    
    def get_bot_status(self) -> Dict:
        """獲取所有機器人狀態"""
        status = {
            'total_bots': len(self.bot_configs),
            'running_bots': len(self.running_processes),
            'agent_mappings': len(self.agent_bot_mapping),
            'bots': {}
        }
        
        for bot_id, config in self.bot_configs.items():
            is_running = bot_id in self.running_processes
            
            status['bots'][bot_id] = {
                'name': config['name'],
                'agent_id': config['agent_id'],
                'running': is_running,
                'database_file': config['database_file']
            }
            
            if is_running:
                process_info = self.running_processes[bot_id]
                status['bots'][bot_id].update({
                    'pid': process_info['process'].pid,
                    'started_at': process_info['started_at'].isoformat(),
                    'uptime': str(datetime.now() - process_info['started_at'])
                })
        
        return status
    
    def add_agent_bot(self, agent_id: str, bot_token: str, usdt_address: str = None):
        """添加新的代理商機器人"""
        bot_id = f'agent_{agent_id}'
        
        self.bot_configs[bot_id] = {
            'token': bot_token,
            'name': f'代理商{agent_id}專屬機器人',
            'agent_id': agent_id,
            'database_file': f'bot_database_agent_{agent_id}.json',
            'admin_ids': [agent_id],
            'usdt_address': usdt_address,
            'api_key': os.getenv('TRONGRID_API_KEY')
        }
        
        self.agent_bot_mapping[agent_id] = bot_id
        
        # 保存配置到文件
        self.save_agent_configs()
        
        logger.info(f"➕ 添加代理商機器人: {agent_id}")
        return bot_id
    
    def remove_agent_bot(self, agent_id: str):
        """移除代理商機器人"""
        bot_id = f'agent_{agent_id}'
        
        # 停止機器人
        if bot_id in self.running_processes:
            self.stop_bot(bot_id)
        
        # 移除配置
        if bot_id in self.bot_configs:
            del self.bot_configs[bot_id]
        
        if agent_id in self.agent_bot_mapping:
            del self.agent_bot_mapping[agent_id]
        
        # 保存配置
        self.save_agent_configs()
        
        logger.info(f"➖ 移除代理商機器人: {agent_id}")
    
    def save_agent_configs(self):
        """保存代理商配置到文件"""
        try:
            agent_configs = {}
            
            for bot_id, config in self.bot_configs.items():
                if config['agent_id']:
                    agent_configs[config['agent_id']] = {
                        'bot_token': config['token'],
                        'name': config['name'],
                        'admin_ids': config['admin_ids'],
                        'usdt_address': config['usdt_address'],
                        'api_key': config['api_key']
                    }
            
            with open('agent_bots_config.json', 'w', encoding='utf-8') as f:
                json.dump(agent_configs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存代理商配置失敗: {e}")
    
    def get_agent_bot(self, agent_id: str) -> Optional[str]:
        """獲取代理商對應的機器人ID"""
        return self.agent_bot_mapping.get(agent_id)
    
    def monitor_bots(self):
        """監控機器人狀態"""
        while True:
            try:
                for bot_id in list(self.running_processes.keys()):
                    process_info = self.running_processes[bot_id]
                    process = process_info['process']
                    
                    # 檢查進程是否還在運行
                    if process.poll() is not None:
                        logger.warning(f"⚠️ 機器人 {bot_id} 意外停止，嘗試重啟...")
                        del self.running_processes[bot_id]
                        
                        # 自動重啟
                        time.sleep(5)
                        self.start_bot(bot_id)
                
                time.sleep(30)  # 每30秒檢查一次
                
            except Exception as e:
                logger.error(f"監控機器人時發生錯誤: {e}")
                time.sleep(60)

def main():
    """主函數"""
    print("🤖 TG旺多機器人管理系統")
    print("=" * 50)
    
    manager = MultiBotManager()
    
    # 顯示配置信息
    status = manager.get_bot_status()
    print(f"📊 機器人配置:")
    print(f"   總機器人數: {status['total_bots']}")
    print(f"   代理商映射: {status['agent_mappings']}")
    
    for bot_id, info in status['bots'].items():
        print(f"   🤖 {info['name']}")
        if info['agent_id']:
            print(f"      └── 代理商: {info['agent_id']}")
    
    print("=" * 50)
    
    try:
        # 啟動所有機器人
        manager.start_all_bots()
        
        # 在背景監控機器人
        monitor_thread = threading.Thread(target=manager.monitor_bots, daemon=True)
        monitor_thread.start()
        
        print("✅ 所有機器人已啟動，按 Ctrl+C 停止")
        
        # 保持主程序運行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 收到停止信號...")
        manager.stop_all_bots()
        print("👋 所有機器人已停止")

if __name__ == "__main__":
    main()