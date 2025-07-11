#!/usr/bin/env python3
"""
TG旺企業管理系統 - 多機器人版
支持多個TG機器人同時管理，代理商專屬機器人分配
"""

import os
import json
import sqlite3
import hashlib
import secrets
import glob
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import subprocess
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 配置
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'tgwang2024')
MANAGER_PASSWORD = os.environ.get('MANAGER_PASSWORD', 'manager123')
AGENT_PASSWORD = os.environ.get('AGENT_PASSWORD', 'agent123')

# 管理員帳號
ADMIN_USERS = {
    "admin": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
    "manager": hashlib.sha256(MANAGER_PASSWORD.encode()).hexdigest(),
    "agent": hashlib.sha256(AGENT_PASSWORD.encode()).hexdigest()
}

# 權限配置
USER_ROLES = {
    "admin": {"name": "超級管理員", "permissions": ["all"]},
    "manager": {"name": "業務經理", "permissions": ["revenue", "customers", "users", "bots"]},
    "agent": {"name": "代理商", "permissions": ["revenue_own", "customers_own", "bot_own"]}
}

class MultiBotDataManager:
    """多機器人數據管理器"""
    
    def __init__(self):
        self.bot_databases = {}
        self.agent_bot_mapping = {}
        self.load_bot_configurations()
    
    def load_bot_configurations(self):
        """載入機器人配置"""
        # 載入主機器人數據
        if os.path.exists('bot_database.json'):
            self.bot_databases['main'] = 'bot_database.json'
        
        # 載入代理商機器人數據
        for db_file in glob.glob('bot_database_agent_*.json'):
            agent_id = db_file.replace('bot_database_agent_', '').replace('.json', '')
            bot_id = f'agent_{agent_id}'
            self.bot_databases[bot_id] = db_file
            self.agent_bot_mapping[agent_id] = bot_id
        
        # 載入代理商配置文件
        if os.path.exists('agent_bots_config.json'):
            try:
                with open('agent_bots_config.json', 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                    for agent_id in configs.keys():
                        if agent_id not in self.agent_bot_mapping:
                            bot_id = f'agent_{agent_id}'
                            db_file = f'bot_database_agent_{agent_id}.json'
                            if os.path.exists(db_file):
                                self.bot_databases[bot_id] = db_file
                                self.agent_bot_mapping[agent_id] = bot_id
            except Exception as e:
                print(f"載入代理商配置失敗: {e}")
    
    def get_bot_database(self, bot_id='main'):
        """獲取指定機器人的數據庫"""
        db_file = self.bot_databases.get(bot_id)
        if not db_file or not os.path.exists(db_file):
            return {
                "users": {},
                "orders": {},
                "activation_codes": {},
                "trial_users": [],
                "transactions": {},
                "statistics": {
                    "total_revenue": 0,
                    "orders_created": 0,
                    "activations_generated": 0
                }
            }
        
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"讀取機器人數據庫失敗 {db_file}: {e}")
            return {
                "users": {},
                "orders": {},
                "activation_codes": {},
                "trial_users": [],
                "transactions": {},
                "statistics": {
                    "total_revenue": 0,
                    "orders_created": 0,
                    "activations_generated": 0
                }
            }
    
    def get_agent_bot_data(self, agent_id):
        """獲取代理商機器人數據"""
        bot_id = self.agent_bot_mapping.get(agent_id)
        if bot_id:
            return self.get_bot_database(bot_id)
        return None
    
    def get_all_bots_data(self):
        """獲取所有機器人的聚合數據"""
        all_data = {
            "total_revenue": 0,
            "total_orders": 0,
            "total_activations": 0,
            "bots": {}
        }
        
        for bot_id, db_file in self.bot_databases.items():
            bot_data = self.get_bot_database(bot_id)
            stats = bot_data.get('statistics', {})
            
            all_data["total_revenue"] += stats.get('total_revenue', 0)
            all_data["total_orders"] += len(bot_data.get('orders', {}))
            all_data["total_activations"] += len(bot_data.get('activation_codes', {}))
            
            all_data["bots"][bot_id] = {
                "revenue": stats.get('total_revenue', 0),
                "orders": len(bot_data.get('orders', {})),
                "activations": len(bot_data.get('activation_codes', {})),
                "agent_id": bot_id.replace('agent_', '') if bot_id.startswith('agent_') else None,
                "database_file": db_file
            }
        
        return all_data
    
    def get_bot_list(self):
        """獲取機器人列表"""
        bots = []
        
        # 載入配置信息
        agent_configs = {}
        if os.path.exists('agent_bots_config.json'):
            try:
                with open('agent_bots_config.json', 'r', encoding='utf-8') as f:
                    agent_configs = json.load(f)
            except:
                pass
        
        for bot_id, db_file in self.bot_databases.items():
            bot_data = self.get_bot_database(bot_id)
            stats = bot_data.get('statistics', {})
            
            if bot_id == 'main':
                bot_info = {
                    "bot_id": bot_id,
                    "name": "TG旺主機器人",
                    "agent_id": None,
                    "agent_name": None,
                    "status": "running",
                    "revenue": stats.get('total_revenue', 0),
                    "orders": len(bot_data.get('orders', {})),
                    "activations": len(bot_data.get('activation_codes', {})),
                    "database_file": db_file
                }
            else:
                agent_id = bot_id.replace('agent_', '')
                config = agent_configs.get(agent_id, {})
                
                bot_info = {
                    "bot_id": bot_id,
                    "name": config.get('name', f'代理商{agent_id}機器人'),
                    "agent_id": agent_id,
                    "agent_name": f"代理商{agent_id}",
                    "status": "running",
                    "revenue": stats.get('total_revenue', 0),
                    "orders": len(bot_data.get('orders', {})),
                    "activations": len(bot_data.get('activation_codes', {})),
                    "database_file": db_file
                }
            
            bots.append(bot_info)
        
        return bots

# 全局數據管理器
data_manager = MultiBotDataManager()

def get_plan_type_chinese(plan_type):
    """轉換方案類型為中文"""
    plan_mapping = {
        'trial': '試用版',
        'weekly': '週方案',
        'monthly': '月方案',
        'quarterly': '季方案',
        'yearly': '年方案',
        'premium': '高級版',
        'enterprise': '企業版'
    }
    return plan_mapping.get(plan_type, plan_type)

# HTML模板
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TG旺多機器人企業管理系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
            overflow: hidden;
            max-width: 400px;
            width: 100%;
        }
        .login-header {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .login-body {
            padding: 30px;
        }
        .logo-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            padding: 12px;
            font-weight: 600;
        }
        .form-control {
            border-radius: 8px;
            padding: 12px;
            border: 2px solid #e9ecef;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <div class="logo-icon">
                <i class="fas fa-robots"></i>
            </div>
            <h2>TG旺多機器人管理系統</h2>
            <p class="mb-0">Multi-Bot Enterprise Portal</p>
        </div>
        <div class="login-body">
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">
                        <i class="fas fa-user me-2"></i>帳號
                    </label>
                    <input type="text" name="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">
                        <i class="fas fa-lock me-2"></i>密碼
                    </label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">
                    <i class="fas fa-sign-in-alt me-2"></i>登入
                </button>
            </form>
            {% if error %}
            <div class="alert alert-danger mt-3">
                <i class="fas fa-exclamation-triangle me-2"></i>{{ error }}
            </div>
            {% endif %}
            <div class="mt-4 text-center">
                <small class="text-muted">
                    <strong>測試帳號:</strong><br>
                    admin/tgwang2024 (管理員)<br>
                    agent/agent123 (代理商)
                </small>
            </div>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TG旺多機器人企業管理系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            background: #f8f9fa; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sidebar {
            background: white;
            min-height: calc(100vh - 70px);
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            position: fixed;
            width: 250px;
            z-index: 1000;
        }
        .main-content {
            margin-left: 250px;
            padding: 20px;
        }
        .nav-link {
            color: #495057;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 2px 8px;
            transition: all 0.3s;
        }
        .nav-link:hover, .nav-link.active {
            background: #667eea;
            color: white;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.3s;
            border-left: 4px solid #667eea;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9rem;
        }
        .data-table {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .table th {
            background: #f8f9fa;
            font-weight: 600;
            border: none;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .bot-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            border-left: 4px solid #28a745;
        }
        .bot-status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #28a745;
            margin-right: 8px;
        }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; }
        }
    </style>
</head>
<body>
    <!-- 導航欄 -->
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid">
            <span class="navbar-brand text-white">
                <i class="fas fa-robots me-2"></i>TG旺多機器人企業管理系統
            </span>
            <div class="navbar-nav ms-auto">
                <span class="text-white me-3">
                    <i class="fas fa-user-circle me-1"></i>{{ username }} ({{ user_role_name }})
                </span>
                <span class="text-white me-3" id="current-time"></span>
                <a href="/logout" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-sign-out-alt me-1"></i>登出
                </a>
            </div>
        </div>
    </nav>

    <!-- 側邊欄 -->
    <div class="sidebar">
        <div class="nav flex-column pt-3">
            <a class="nav-link active" href="#" onclick="switchTab('dashboard')">
                <i class="fas fa-tachometer-alt me-2"></i>總覽儀表板
            </a>
            <a class="nav-link" href="#" onclick="switchTab('bots')">
                <i class="fas fa-robot me-2"></i>機器人管理
            </a>
            <a class="nav-link" href="#" onclick="switchTab('orders')">
                <i class="fas fa-shopping-cart me-2"></i>訂單管理
            </a>
            <a class="nav-link" href="#" onclick="switchTab('activations')">
                <i class="fas fa-key me-2"></i>激活碼管理
            </a>
            {% if 'all' in permissions or 'bots' in permissions %}
            <a class="nav-link" href="#" onclick="switchTab('agents')">
                <i class="fas fa-users-cog me-2"></i>代理商管理
            </a>
            {% endif %}
        </div>
    </div>

    <!-- 主要內容 -->
    <div class="main-content">
        <!-- 總覽儀表板 -->
        <div id="dashboard-tab" class="tab-content active">
            <div class="row mb-4">
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-revenue">0 TRX</div>
                                <div class="stat-label">總收入</div>
                            </div>
                            <i class="fas fa-dollar-sign fa-2x text-success"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-orders">0</div>
                                <div class="stat-label">總訂單數</div>
                            </div>
                            <i class="fas fa-shopping-cart fa-2x text-primary"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-activations">0</div>
                                <div class="stat-label">激活碼總數</div>
                            </div>
                            <i class="fas fa-key fa-2x text-warning"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-bots">0</div>
                                <div class="stat-label">機器人數量</div>
                            </div>
                            <i class="fas fa-robot fa-2x text-info"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <h5>機器人狀態概覽</h5>
                    <div id="bots-overview">
                        <!-- 動態載入機器人狀態 -->
                    </div>
                </div>
            </div>
        </div>

        <!-- 機器人管理 -->
        <div id="bots-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-robot me-2"></i>機器人管理</h3>
                {% if 'all' in permissions %}
                <button class="btn btn-primary" onclick="addNewBot()">
                    <i class="fas fa-plus me-1"></i>添加機器人
                </button>
                {% endif %}
            </div>
            
            <div id="bots-list">
                <!-- 動態載入機器人列表 -->
            </div>
        </div>

        <!-- 訂單管理 -->
        <div id="orders-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-shopping-cart me-2"></i>訂單管理</h3>
                <div>
                    <select class="form-select d-inline-block me-2" style="width: auto;" id="bot-filter">
                        <option value="">所有機器人</option>
                    </select>
                    <button class="btn btn-success" onclick="exportOrders()">
                        <i class="fas fa-download me-1"></i>導出
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>機器人</th>
                                <th>訂單編號</th>
                                <th>用戶ID</th>
                                <th>方案類型</th>
                                <th>金額</th>
                                <th>狀態</th>
                                <th>創建時間</th>
                            </tr>
                        </thead>
                        <tbody id="orders-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 激活碼管理 -->
        <div id="activations-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-key me-2"></i>激活碼管理</h3>
                <div>
                    <select class="form-select d-inline-block me-2" style="width: auto;" id="activation-bot-filter">
                        <option value="">所有機器人</option>
                    </select>
                    <button class="btn btn-success" onclick="exportActivations()">
                        <i class="fas fa-download me-1"></i>導出
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>機器人</th>
                                <th>激活碼</th>
                                <th>方案類型</th>
                                <th>狀態</th>
                                <th>創建時間</th>
                                <th>到期時間</th>
                            </tr>
                        </thead>
                        <tbody id="activations-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if 'all' in permissions or 'bots' in permissions %}
        <!-- 代理商管理 -->
        <div id="agents-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-users-cog me-2"></i>代理商管理</h3>
                {% if 'all' in permissions %}
                <button class="btn btn-primary" onclick="addNewAgent()">
                    <i class="fas fa-plus me-1"></i>添加代理商
                </button>
                {% endif %}
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>代理商ID</th>
                                <th>機器人名稱</th>
                                <th>總收入</th>
                                <th>訂單數</th>
                                <th>激活碼數</th>
                                <th>狀態</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="agents-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentTab = 'dashboard';
        
        // 時間更新
        function updateTime() {
            document.getElementById('current-time').textContent = 
                new Date().toLocaleString('zh-TW');
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        // 標籤切換
        function switchTab(tabName) {
            // 更新導航狀態
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // 更新內容顯示
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName + '-tab').classList.add('active');
            
            currentTab = tabName;
            loadTabData(tabName);
        }
        
        // 載入數據
        async function loadTabData(tabName) {
            try {
                switch(tabName) {
                    case 'dashboard':
                        await loadDashboardData();
                        break;
                    case 'bots':
                        await loadBotsData();
                        break;
                    case 'orders':
                        await loadOrdersData();
                        break;
                    case 'activations':
                        await loadActivationsData();
                        break;
                    case 'agents':
                        await loadAgentsData();
                        break;
                }
            } catch (error) {
                console.error('載入數據失敗:', error);
            }
        }
        
        // 載入儀表板數據
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                document.getElementById('total-revenue').textContent = data.total_revenue + ' TRX';
                document.getElementById('total-orders').textContent = data.total_orders;
                document.getElementById('total-activations').textContent = data.total_activations;
                document.getElementById('total-bots').textContent = data.total_bots;
                
                // 更新機器人概覽
                updateBotsOverview(data.bots || []);
                
            } catch (error) {
                console.error('載入儀表板數據失敗:', error);
            }
        }
        
        // 載入機器人數據
        async function loadBotsData() {
            try {
                const response = await fetch('/api/bots');
                const data = await response.json();
                updateBotsList(data.bots || []);
            } catch (error) {
                console.error('載入機器人數據失敗:', error);
            }
        }
        
        // 載入訂單數據
        async function loadOrdersData() {
            try {
                const response = await fetch('/api/orders');
                const data = await response.json();
                updateOrdersTable(data.orders || []);
                updateBotFilter(data.bots || []);
            } catch (error) {
                console.error('載入訂單數據失敗:', error);
            }
        }
        
        // 載入激活碼數據
        async function loadActivationsData() {
            try {
                const response = await fetch('/api/activations');
                const data = await response.json();
                updateActivationsTable(data.activations || []);
                updateActivationBotFilter(data.bots || []);
            } catch (error) {
                console.error('載入激活碼數據失敗:', error);
            }
        }
        
        // 更新機器人概覽
        function updateBotsOverview(bots) {
            const container = document.getElementById('bots-overview');
            container.innerHTML = '';
            
            bots.forEach(bot => {
                const card = `
                    <div class="bot-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6><span class="bot-status"></span>${bot.name}</h6>
                                <small class="text-muted">${bot.agent_id ? '代理商: ' + bot.agent_id : '主機器人'}</small>
                            </div>
                            <div class="text-end">
                                <div><strong>${bot.revenue} TRX</strong></div>
                                <small>${bot.orders} 訂單 | ${bot.activations} 激活碼</small>
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += card;
            });
        }
        
        // 更新機器人列表
        function updateBotsList(bots) {
            const container = document.getElementById('bots-list');
            container.innerHTML = '';
            
            bots.forEach(bot => {
                const card = `
                    <div class="bot-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5><span class="bot-status"></span>${bot.name}</h5>
                                <p class="mb-1">${bot.agent_id ? '代理商: ' + bot.agent_name : '主機器人'}</p>
                                <small class="text-muted">數據庫: ${bot.database_file}</small>
                            </div>
                            <div class="text-end">
                                <div class="mb-2">
                                    <span class="badge bg-success">${bot.status}</span>
                                </div>
                                <div><strong>${bot.revenue} TRX</strong></div>
                                <small>${bot.orders} 訂單 | ${bot.activations} 激活碼</small>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-info me-1" onclick="viewBotDetails('${bot.bot_id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                {% if 'all' in permissions %}
                                <button class="btn btn-sm btn-warning" onclick="manageBotSettings('${bot.bot_id}')">
                                    <i class="fas fa-cog"></i>
                                </button>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += card;
            });
        }
        
        // 更新訂單表格
        function updateOrdersTable(orders) {
            const tbody = document.getElementById('orders-tbody');
            tbody.innerHTML = '';
            
            orders.forEach(order => {
                const row = `
                    <tr>
                        <td><span class="badge bg-primary">${order.bot_name}</span></td>
                        <td><code>${order.order_id}</code></td>
                        <td>${order.user_id}</td>
                        <td><span class="badge bg-info">${order.plan_type_chinese}</span></td>
                        <td>${order.amount} ${order.currency}</td>
                        <td><span class="badge ${order.status === 'paid' ? 'bg-success' : 'bg-warning'}">${order.status === 'paid' ? '已付款' : '待付款'}</span></td>
                        <td>${new Date(order.created_at).toLocaleDateString('zh-TW')}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新激活碼表格
        function updateActivationsTable(activations) {
            const tbody = document.getElementById('activations-tbody');
            tbody.innerHTML = '';
            
            activations.forEach(activation => {
                const row = `
                    <tr>
                        <td><span class="badge bg-primary">${activation.bot_name}</span></td>
                        <td><code>${activation.activation_code}</code></td>
                        <td><span class="badge bg-info">${activation.plan_type_chinese}</span></td>
                        <td><span class="badge ${activation.used ? 'bg-danger' : 'bg-success'}">${activation.used ? '已使用' : '未使用'}</span></td>
                        <td>${new Date(activation.created_at).toLocaleDateString('zh-TW')}</td>
                        <td>${new Date(activation.expires_at).toLocaleDateString('zh-TW')}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新過濾器
        function updateBotFilter(bots) {
            const select = document.getElementById('bot-filter');
            select.innerHTML = '<option value="">所有機器人</option>';
            bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.bot_id}">${bot.name}</option>`;
            });
        }
        
        function updateActivationBotFilter(bots) {
            const select = document.getElementById('activation-bot-filter');
            select.innerHTML = '<option value="">所有機器人</option>';
            bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.bot_id}">${bot.name}</option>`;
            });
        }
        
        // 按鈕功能
        function addNewBot() { alert('添加新機器人功能開發中...'); }
        function addNewAgent() { alert('添加新代理商功能開發中...'); }
        function viewBotDetails(botId) { alert('查看機器人詳情: ' + botId); }
        function manageBotSettings(botId) { alert('管理機器人設置: ' + botId); }
        function exportOrders() { alert('導出訂單功能開發中...'); }
        function exportActivations() { alert('導出激活碼功能開發中...'); }
        
        // 初始化
        window.onload = function() {
            loadDashboardData();
        };
    </script>
</body>
</html>
'''

# API路由
@app.route('/api/dashboard')
def api_dashboard():
    """儀表板API - 多機器人數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        all_data = data_manager.get_all_bots_data()
        bots_list = data_manager.get_bot_list()
        
        return jsonify({
            'total_revenue': all_data['total_revenue'],
            'total_orders': all_data['total_orders'],
            'total_activations': all_data['total_activations'],
            'total_bots': len(bots_list),
            'bots': bots_list
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bots')
def api_bots():
    """機器人API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bots_list = data_manager.get_bot_list()
        return jsonify({'bots': bots_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def api_orders():
    """訂單API - 多機器人訂單數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        all_orders = []
        bots_list = data_manager.get_bot_list()
        
        for bot in bots_list:
            bot_data = data_manager.get_bot_database(bot['bot_id'])
            orders = bot_data.get('orders', {})
            
            for order_id, order_data in orders.items():
                all_orders.append({
                    'bot_id': bot['bot_id'],
                    'bot_name': bot['name'],
                    'order_id': order_data.get('order_id'),
                    'user_id': order_data.get('user_id'),
                    'plan_type': order_data.get('plan_type'),
                    'plan_type_chinese': get_plan_type_chinese(order_data.get('plan_type')),
                    'amount': order_data.get('amount'),
                    'currency': order_data.get('currency'),
                    'status': order_data.get('status'),
                    'created_at': order_data.get('created_at')
                })
        
        # 按創建時間排序
        all_orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'orders': all_orders,
            'bots': bots_list
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activations')
def api_activations():
    """激活碼API - 多機器人激活碼數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        all_activations = []
        bots_list = data_manager.get_bot_list()
        
        for bot in bots_list:
            bot_data = data_manager.get_bot_database(bot['bot_id'])
            activation_codes = bot_data.get('activation_codes', {})
            
            for code, code_data in activation_codes.items():
                all_activations.append({
                    'bot_id': bot['bot_id'],
                    'bot_name': bot['name'],
                    'activation_code': code_data.get('activation_code'),
                    'plan_type': code_data.get('plan_type'),
                    'plan_type_chinese': get_plan_type_chinese(code_data.get('plan_type')),
                    'used': code_data.get('used', False),
                    'created_at': code_data.get('created_at'),
                    'expires_at': code_data.get('expires_at')
                })
        
        # 按創建時間排序
        all_activations.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'activations': all_activations,
            'bots': bots_list
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 基本路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登入"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username in ADMIN_USERS and ADMIN_USERS[username] == password_hash:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='帳號或密碼錯誤')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/')
def index():
    """首頁"""
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """儀表板"""
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    
    username = session.get('username')
    user_role_info = USER_ROLES.get(username, USER_ROLES['agent'])
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                username=username,
                                user_role=username,
                                user_role_name=user_role_info['name'],
                                permissions=user_role_info['permissions'])

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🤖 TG旺多機器人企業管理系統")
    print("=" * 60)
    print("🔗 支持多機器人同時管理:")
    print("   ✅ 主機器人數據")
    print("   ✅ 代理商專屬機器人")
    print("   ✅ 統一數據管理")
    print("   ✅ 權限分級控制")
    print("=" * 60)
    
    # 重新載入數據管理器
    data_manager.load_bot_configurations()
    
    # 顯示發現的機器人
    bots_list = data_manager.get_bot_list()
    print(f"📋 發現 {len(bots_list)} 個機器人:")
    for bot in bots_list:
        print(f"   🤖 {bot['name']}")
        if bot['agent_id']:
            print(f"      └── 代理商: {bot['agent_id']}")
        print(f"      └── 數據庫: {bot['database_file']}")
    
    print("=" * 60)
    print("📌 預設帳號:")
    print(f"   admin/{ADMIN_PASSWORD} (超級管理員)")
    print(f"   agent/{AGENT_PASSWORD} (代理商)")
    print("=" * 60)
    
    # 獲取端口
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)