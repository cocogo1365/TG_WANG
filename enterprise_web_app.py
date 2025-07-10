#!/usr/bin/env python3
"""
TG旺企業管理網站 - Railway部署版
完整的企業級管理系統，包含收入統計、客戶管理、代理系統
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 配置
DATABASE_URL = os.environ.get('DATABASE_URL', 'enterprise_management.db')
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
    "manager": {"name": "業務經理", "permissions": ["revenue", "customers", "users"]},
    "agent": {"name": "代理商", "permissions": ["revenue_own", "customers_own"]}
}

def init_database():
    """初始化資料庫"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 客戶訂單表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_email TEXT,
            customer_telegram TEXT,
            plan_type TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            payment_method TEXT,
            payment_hash TEXT,
            payment_status TEXT DEFAULT 'pending',
            activation_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            expires_at TIMESTAMP,
            agent_id TEXT,
            device_limit INTEGER DEFAULT 1,
            features TEXT,
            notes TEXT
        )
    ''')
    
    # 用戶狀態表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_code TEXT UNIQUE NOT NULL,
            device_id TEXT,
            device_ip TEXT,
            status TEXT DEFAULT 'active',
            banned_reason TEXT,
            banned_at TIMESTAMP,
            banned_by TEXT,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            violation_count INTEGER DEFAULT 0,
            auto_ban_triggers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 代理商表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE NOT NULL,
            agent_name TEXT NOT NULL,
            agent_email TEXT,
            agent_telegram TEXT,
            commission_rate DECIMAL(5,2) DEFAULT 10.00,
            total_sales DECIMAL(10,2) DEFAULT 0.00,
            total_commission DECIMAL(10,2) DEFAULT 0.00,
            status TEXT DEFAULT 'active',
            bot_token TEXT,
            bot_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 系統日誌表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_sample_data():
    """創建示例數據"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 檢查是否已有數據
    cursor.execute('SELECT COUNT(*) FROM customer_orders')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    import uuid
    
    # 示例代理商
    agents = [
        ('AGENT001', '張代理', 'zhang@example.com', '@zhangagent', 15.0),
        ('AGENT002', '李代理', 'li@example.com', '@liagent', 12.0),
        ('AGENT003', '王代理', 'wang@example.com', '@wangagent', 10.0)
    ]
    
    for agent in agents:
        try:
            cursor.execute('''
                INSERT INTO agents (agent_id, agent_name, agent_email, agent_telegram, commission_rate)
                VALUES (?, ?, ?, ?, ?)
            ''', agent)
        except sqlite3.IntegrityError:
            pass
    
    # 示例訂單
    plans = ['基礎版', '專業版', '旗艦版']
    prices = [29, 59, 99]
    payment_methods = ['USDT', 'BTC', 'ETH', '信用卡']
    
    for i in range(15):
        order_id = f"ORDER_{uuid.uuid4().hex[:8].upper()}"
        activation_code = f"TG{uuid.uuid4().hex[:12].upper()}"
        plan_idx = i % 3
        
        # 隨機分配代理商
        agent_id = agents[i % 3][0] if i % 4 != 0 else None
        
        cursor.execute('''
            INSERT INTO customer_orders (
                order_id, customer_name, customer_email, plan_type, price, 
                payment_method, payment_status, activation_code, 
                created_at, expires_at, agent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            f"客戶{i+1}",
            f"customer{i+1}@example.com",
            plans[plan_idx],
            prices[plan_idx],
            payment_methods[i % 4],
            'paid' if i % 3 != 0 else 'pending',
            activation_code,
            datetime.now() - timedelta(days=i*2),
            datetime.now() + timedelta(days=365),
            agent_id
        ))
        
        # 對應的用戶狀態
        cursor.execute('''
            INSERT INTO user_status (
                activation_code, device_id, device_ip, status, last_activity
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            activation_code,
            f"device_{uuid.uuid4().hex[:12]}",
            f"192.168.1.{100+i}",
            'active' if i % 7 != 0 else ('banned' if i % 10 == 0 else 'warning'),
            datetime.now() - timedelta(hours=i*2)
        ))
    
    conn.commit()
    conn.close()

# HTML模板
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TG旺企業管理系統</title>
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
                <i class="fas fa-building"></i>
            </div>
            <h2>TG旺企業管理系統</h2>
            <p class="mb-0">Enterprise Management Portal</p>
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
    <title>TG旺企業管理系統</title>
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
        .badge-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .chart-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            height: 400px;
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
                <i class="fas fa-building me-2"></i>TG旺企業管理系統
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
                <i class="fas fa-tachometer-alt me-2"></i>儀表板
            </a>
            <a class="nav-link" href="#" onclick="switchTab('revenue')">
                <i class="fas fa-chart-line me-2"></i>收入統計
            </a>
            <a class="nav-link" href="#" onclick="switchTab('customers')">
                <i class="fas fa-users me-2"></i>客戶管理
            </a>
            {% if 'users' in permissions %}
            <a class="nav-link" href="#" onclick="switchTab('users')">
                <i class="fas fa-user-shield me-2"></i>用戶狀態
            </a>
            {% endif %}
            {% if 'all' in permissions %}
            <a class="nav-link" href="#" onclick="switchTab('agents')">
                <i class="fas fa-handshake me-2"></i>代理業務
            </a>
            <a class="nav-link" href="#" onclick="switchTab('security')">
                <i class="fas fa-shield-alt me-2"></i>安全監控
            </a>
            <a class="nav-link" href="#" onclick="switchTab('reports')">
                <i class="fas fa-file-chart me-2"></i>報告中心
            </a>
            {% endif %}
        </div>
    </div>

    <!-- 主要內容 -->
    <div class="main-content">
        <!-- 儀表板概覽 -->
        <div id="dashboard-tab" class="tab-content active">
            <div class="row mb-4">
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="total-revenue">$0</div>
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
                                <div class="stat-value" id="total-customers">0</div>
                                <div class="stat-label">總客戶數</div>
                            </div>
                            <i class="fas fa-users fa-2x text-primary"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="stat-card">
                        <div class="d-flex justify-content-between">
                            <div>
                                <div class="stat-value" id="active-codes">0</div>
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
                                <div class="stat-value" id="monthly-growth">0%</div>
                                <div class="stat-label">月成長率</div>
                            </div>
                            <i class="fas fa-chart-line fa-2x text-info"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-8 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">收入趨勢</h5>
                        <canvas id="revenueChart"></canvas>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">方案分布</h5>
                        <canvas id="planChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- 收入統計 -->
        <div id="revenue-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-chart-line me-2"></i>收入統計</h3>
                <div>
                    {% if user_role == 'admin' %}
                    <button class="btn btn-primary me-2" onclick="addOrder()">
                        <i class="fas fa-plus me-1"></i>新增訂單
                    </button>
                    {% endif %}
                    <button class="btn btn-success" onclick="exportRevenue()">
                        <i class="fas fa-download me-1"></i>導出報告
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>訂單編號</th>
                                <th>客戶名稱</th>
                                <th>方案類型</th>
                                <th>金額</th>
                                <th>支付方式</th>
                                <th>狀態</th>
                                <th>日期</th>
                                <th>代理商</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="revenue-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 客戶管理 -->
        <div id="customers-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-users me-2"></i>客戶管理</h3>
                <div class="d-flex gap-2">
                    <input type="text" class="form-control" placeholder="搜索客戶..." id="customer-search" style="width: 200px;">
                    <button class="btn btn-info" onclick="searchCustomers()">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-success" onclick="exportCustomers()">
                        <i class="fas fa-download me-1"></i>導出
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>客戶信息</th>
                                <th>方案</th>
                                <th>設備ID</th>
                                <th>IP地址</th>
                                <th>狀態</th>
                                <th>到期日</th>
                                <th>最後活動</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="customers-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if 'users' in permissions %}
        <!-- 用戶狀態 -->
        <div id="users-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-user-shield me-2"></i>用戶狀態管理</h3>
                <div>
                    {% if user_role == 'admin' %}
                    <button class="btn btn-warning me-2" onclick="autobanSettings()">
                        <i class="fas fa-cog me-1"></i>自動停權設置
                    </button>
                    {% endif %}
                    <button class="btn btn-info" onclick="refreshUsers()">
                        <i class="fas fa-refresh me-1"></i>刷新
                    </button>
                </div>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>設備ID</th>
                                <th>IP地址</th>
                                <th>狀態</th>
                                <th>違規次數</th>
                                <th>最後活動</th>
                                <th>停權原因</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="users-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}

        {% if 'all' in permissions %}
        <!-- 代理業務 -->
        <div id="agents-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-handshake me-2"></i>代理業務管理</h3>
                <button class="btn btn-primary" onclick="addAgent()">
                    <i class="fas fa-plus me-1"></i>新增代理
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>代理ID</th>
                                <th>代理名稱</th>
                                <th>聯繫信息</th>
                                <th>佣金率</th>
                                <th>總銷售</th>
                                <th>總佣金</th>
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
                    case 'revenue':
                        await loadRevenueData();
                        break;
                    case 'customers':
                        await loadCustomersData();
                        break;
                    case 'users':
                        await loadUsersData();
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
                
                document.getElementById('total-revenue').textContent = '$' + (data.total_revenue || 0).toLocaleString();
                document.getElementById('total-customers').textContent = data.total_customers || 0;
                document.getElementById('active-codes').textContent = data.active_codes || 0;
                document.getElementById('monthly-growth').textContent = (data.monthly_growth || 0) + '%';
                
                // 更新圖表
                updateRevenueChart(data.revenue_chart || []);
                updatePlanChart(data.plan_distribution || {});
                
            } catch (error) {
                console.error('載入儀表板數據失敗:', error);
            }
        }
        
        // 載入收入數據
        async function loadRevenueData() {
            try {
                const response = await fetch('/api/revenue');
                const data = await response.json();
                updateRevenueTable(data.orders || []);
            } catch (error) {
                console.error('載入收入數據失敗:', error);
            }
        }
        
        // 載入客戶數據
        async function loadCustomersData() {
            try {
                const response = await fetch('/api/customers');
                const data = await response.json();
                updateCustomersTable(data.customers || []);
            } catch (error) {
                console.error('載入客戶數據失敗:', error);
            }
        }
        
        // 更新收入表格
        function updateRevenueTable(orders) {
            const tbody = document.getElementById('revenue-tbody');
            tbody.innerHTML = '';
            
            orders.forEach(order => {
                const row = `
                    <tr>
                        <td>${order.order_id}</td>
                        <td>${order.customer_name}</td>
                        <td><span class="badge bg-primary">${order.plan_type}</span></td>
                        <td>$${order.price}</td>
                        <td>${order.payment_method}</td>
                        <td>
                            <span class="badge ${order.payment_status === 'paid' ? 'bg-success' : 'bg-warning'}">
                                ${order.payment_status === 'paid' ? '已付款' : '待付款'}
                            </span>
                        </td>
                        <td>${new Date(order.created_at).toLocaleDateString('zh-TW')}</td>
                        <td>${order.agent_id || '直銷'}</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewOrder('${order.order_id}')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新客戶表格
        function updateCustomersTable(customers) {
            const tbody = document.getElementById('customers-tbody');
            tbody.innerHTML = '';
            
            customers.forEach(customer => {
                const statusClass = customer.status === 'active' ? 'bg-success' : 
                                   customer.status === 'banned' ? 'bg-danger' : 'bg-warning';
                
                const row = `
                    <tr>
                        <td><code>${customer.activation_code}</code></td>
                        <td>
                            <div>${customer.customer_name}</div>
                            <small class="text-muted">${customer.customer_email}</small>
                        </td>
                        <td><span class="badge bg-info">${customer.plan_type}</span></td>
                        <td><code>${customer.device_id ? customer.device_id.slice(0, 12) + '...' : 'N/A'}</code></td>
                        <td>${customer.device_ip || 'N/A'}</td>
                        <td><span class="badge ${statusClass}">${customer.status}</span></td>
                        <td>${customer.expires_at ? new Date(customer.expires_at).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>${customer.last_activity ? new Date(customer.last_activity).toLocaleDateString('zh-TW') : 'N/A'}</td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-info" onclick="viewCustomer('${customer.activation_code}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                {% if user_role != 'agent' %}
                                <button class="btn btn-${customer.status === 'active' ? 'danger' : 'success'}" 
                                        onclick="${customer.status === 'active' ? 'banCustomer' : 'unbanCustomer'}('${customer.activation_code}')">
                                    <i class="fas fa-${customer.status === 'active' ? 'ban' : 'check'}"></i>
                                </button>
                                {% endif %}
                            </div>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 圖表更新
        function updateRevenueChart(data) {
            const ctx = document.getElementById('revenueChart').getContext('2d');
            if (window.revenueChart) window.revenueChart.destroy();
            
            window.revenueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [{
                        label: '每日收入',
                        data: data.map(d => d.amount),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
        
        function updatePlanChart(data) {
            const ctx = document.getElementById('planChart').getContext('2d');
            if (window.planChart) window.planChart.destroy();
            
            window.planChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data),
                    datasets: [{
                        data: Object.values(data),
                        backgroundColor: ['#667eea', '#764ba2', '#f093fb']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
        
        // 按鈕功能
        function addOrder() { alert('新增訂單功能開發中...'); }
        function exportRevenue() { alert('導出收入報告功能開發中...'); }
        function searchCustomers() { 
            const term = document.getElementById('customer-search').value;
            alert('搜索: ' + term); 
        }
        function exportCustomers() { alert('導出客戶數據功能開發中...'); }
        function viewOrder(id) { alert('查看訂單: ' + id); }
        function viewCustomer(code) { alert('查看客戶: ' + code); }
        function banCustomer(code) { 
            if (confirm('確定要停權此客戶嗎？')) {
                alert('已停權: ' + code);
                loadCustomersData();
            }
        }
        function unbanCustomer(code) { 
            if (confirm('確定要解除停權嗎？')) {
                alert('已解除停權: ' + code);
                loadCustomersData();
            }
        }
        
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
    """儀表板API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT SUM(price) FROM customer_orders WHERE payment_status = "paid"')
        total_revenue = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM customer_orders')
        total_customers = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM user_status WHERE status = "active"')
        active_codes = cursor.fetchone()[0] or 0
        
        # 收入趨勢 (最近7天)
        cursor.execute('''
            SELECT DATE(created_at) as date, SUM(price) as amount
            FROM customer_orders 
            WHERE payment_status = 'paid' AND created_at >= date('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        revenue_chart = [{'date': row[0], 'amount': row[1]} for row in cursor.fetchall()]
        
        # 方案分布
        cursor.execute('''
            SELECT plan_type, COUNT(*) as count
            FROM customer_orders
            GROUP BY plan_type
        ''')
        plan_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_customers': total_customers,
            'active_codes': active_codes,
            'monthly_growth': 15.2,  # 模擬數據
            'revenue_chart': revenue_chart,
            'plan_distribution': plan_distribution
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/revenue')
def api_revenue():
    """收入API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 根據用戶權限過濾數據
        user_role = session.get('username')
        if user_role == 'agent':
            # 代理商只能看自己的訂單
            cursor.execute('''
                SELECT order_id, customer_name, plan_type, price, payment_method, 
                       payment_status, created_at, agent_id
                FROM customer_orders 
                WHERE agent_id = ?
                ORDER BY created_at DESC
            ''', (f'AGENT_USER_{user_role}',))
        else:
            cursor.execute('''
                SELECT order_id, customer_name, plan_type, price, payment_method, 
                       payment_status, created_at, agent_id
                FROM customer_orders 
                ORDER BY created_at DESC
                LIMIT 50
            ''')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'order_id': row[0],
                'customer_name': row[1],
                'plan_type': row[2],
                'price': row[3],
                'payment_method': row[4],
                'payment_status': row[5],
                'created_at': row[6],
                'agent_id': row[7]
            })
        
        conn.close()
        return jsonify({'orders': orders})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers')
def api_customers():
    """客戶API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 聯接查詢
        cursor.execute('''
            SELECT co.activation_code, co.customer_name, co.customer_email, 
                   co.plan_type, co.expires_at, co.agent_id,
                   us.device_id, us.device_ip, us.status, us.last_activity
            FROM customer_orders co
            LEFT JOIN user_status us ON co.activation_code = us.activation_code
            ORDER BY co.created_at DESC
        ''')
        
        customers = []
        for row in cursor.fetchall():
            customers.append({
                'activation_code': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'plan_type': row[3],
                'expires_at': row[4],
                'agent_id': row[5],
                'device_id': row[6],
                'device_ip': row[7],
                'status': row[8] or 'unknown',
                'last_activity': row[9]
            })
        
        conn.close()
        return jsonify({'customers': customers})
        
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
            
            # 記錄登入日誌
            log_action(username, 'login', request.remote_addr)
            
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
    username = session.get('username')
    if username:
        log_action(username, 'logout', request.remote_addr)
    
    session.clear()
    return redirect(url_for('login'))

def log_action(user_id, action, ip_address, details=None):
    """記錄操作日誌"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (user_id, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action, details, ip_address))
        conn.commit()
        conn.close()
    except:
        pass

if __name__ == '__main__':
    print("🚀 TG旺企業管理系統 - Railway版")
    print("=" * 50)
    print("🌐 Railway部署版本")
    print("📱 響應式設計，支持手機訪問")
    print("🔐 多層級權限管理")
    print("📊 實時數據統計")
    print("=" * 50)
    print("📌 預設帳號:")
    print(f"   admin/{ADMIN_PASSWORD} (超級管理員)")
    print(f"   manager/{MANAGER_PASSWORD} (業務經理)")
    print(f"   agent/{AGENT_PASSWORD} (代理商)")
    print("=" * 50)
    
    # 初始化
    init_database()
    create_sample_data()
    
    # 獲取端口
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)