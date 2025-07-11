#!/usr/bin/env python3
"""
TG旺企業管理系統 - 整合TG機器人數據版
串聯機器人數據，顯示真實的訂單、激活碼、用戶數據
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
from database_adapter import DatabaseAdapter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 初始化數據庫適配器
db_adapter = DatabaseAdapter()

# 配置
BOT_DATABASE_PATH = os.environ.get('BOT_DATABASE_PATH', 'bot_database.json')
UPLOAD_DATA_DIR = os.environ.get('UPLOAD_DATA_DIR', 'uploaded_data')
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

def get_bot_database():
    """獲取機器人數據庫"""
    try:
        # 優先使用數據庫適配器
        db_data = db_adapter.get_activation_codes()
        
        # 如果有PostgreSQL數據，使用它
        if db_data and db_data.get("activation_codes"):
            # 補充其他必要字段
            if os.path.exists(BOT_DATABASE_PATH):
                with open(BOT_DATABASE_PATH, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    # 合併數據：激活碼使用PostgreSQL，其他使用本地
                    local_data["activation_codes"] = db_data["activation_codes"]
                    return local_data
            else:
                return {
                    "users": {},
                    "orders": {},
                    "activation_codes": db_data["activation_codes"],
                    "trial_users": [],
                    "transactions": {},
                    "statistics": {
                        "total_revenue": 0,
                        "orders_created": 0,
                        "activations_generated": 0
                    }
                }
        
        # 降級到本地JSON文件
        if os.path.exists(BOT_DATABASE_PATH):
            with open(BOT_DATABASE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
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
    except Exception as e:
        print(f"讀取機器人數據庫失敗: {e}")
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

def get_uploaded_data():
    """獲取上傳的採集數據"""
    uploaded_data = []
    
    try:
        if os.path.exists(UPLOAD_DATA_DIR):
            for filename in os.listdir(UPLOAD_DATA_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(UPLOAD_DATA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            uploaded_data.append(data)
                    except Exception as e:
                        print(f"讀取上傳數據失敗 {filename}: {e}")
    except Exception as e:
        print(f"讀取上傳目錄失敗: {e}")
    
    return uploaded_data

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

def format_currency(amount, currency='TRX'):
    """格式化貨幣顯示"""
    if currency == 'TRX':
        return f"{amount:.2f} TRX"
    elif currency == 'USDT':
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"

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
                <i class="fab fa-telegram-plane"></i>
            </div>
            <h2>TG旺企業管理系統</h2>
            <p class="mb-0">整合機器人數據管理</p>
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
    <title>TG旺企業管理系統 - 機器人數據整合</title>
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
        .status-paid { background: #d4edda; color: #155724; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-active { background: #d1ecf1; color: #0c5460; }
        .status-used { background: #f8d7da; color: #721c24; }
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
                <i class="fab fa-telegram-plane me-2"></i>TG旺企業管理系統 (機器人數據整合)
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
            <a class="nav-link" href="#" onclick="switchTab('orders')">
                <i class="fas fa-shopping-cart me-2"></i>TG機器人訂單
            </a>
            <a class="nav-link" href="#" onclick="switchTab('activations')">
                <i class="fas fa-key me-2"></i>激活碼管理
            </a>
            <a class="nav-link" href="#" onclick="switchTab('collected-data')">
                <i class="fas fa-database me-2"></i>採集數據
            </a>
            {% if 'all' in permissions %}
            <a class="nav-link" href="#" onclick="switchTab('statistics')">
                <i class="fas fa-chart-pie me-2"></i>統計分析
            </a>
            <a class="nav-link" href="#" onclick="switchTab('users')">
                <i class="fas fa-users me-2"></i>用戶管理
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
                                <div class="stat-value" id="collected-members">0</div>
                                <div class="stat-label">採集成員數</div>
                            </div>
                            <i class="fas fa-users fa-2x text-info"></i>
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

        <!-- TG機器人訂單 -->
        <div id="orders-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-shopping-cart me-2"></i>TG機器人訂單</h3>
                <button class="btn btn-success" onclick="refreshOrders()">
                    <i class="fas fa-refresh me-1"></i>刷新數據
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>訂單編號</th>
                                <th>用戶ID</th>
                                <th>方案類型</th>
                                <th>金額</th>
                                <th>貨幣</th>
                                <th>狀態</th>
                                <th>交易哈希</th>
                                <th>創建時間</th>
                                <th>到期時間</th>
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
                    <input type="text" class="form-control d-inline-block" placeholder="搜索激活碼..." id="activation-search" style="width: 200px;">
                    <button class="btn btn-info ms-2" onclick="searchActivations()">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-success ms-2" onclick="refreshActivations()">
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
                                <th>方案類型</th>
                                <th>狀態</th>
                                <th>有效期</th>
                                <th>使用狀態</th>
                                <th>創建時間</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="activations-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 採集數據 -->
        <div id="collected-data-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-database me-2"></i>採集數據管理</h3>
                <button class="btn btn-success" onclick="refreshCollectedData()">
                    <i class="fas fa-refresh me-1"></i>刷新數據
                </button>
            </div>
            
            <div class="data-table">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>激活碼</th>
                                <th>設備信息</th>
                                <th>採集方法</th>
                                <th>目標群組</th>
                                <th>採集數量</th>
                                <th>上傳時間</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="collected-data-tbody">
                            <!-- 動態載入 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if 'all' in permissions %}
        <!-- 統計分析 -->
        <div id="statistics-tab" class="tab-content">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3><i class="fas fa-chart-pie me-2"></i>統計分析</h3>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">每日訂單趨勢</h5>
                        <canvas id="dailyOrdersChart"></canvas>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="chart-container">
                        <h5 class="mb-3">激活碼使用率</h5>
                        <canvas id="activationRateChart"></canvas>
                    </div>
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
                    case 'orders':
                        await loadOrdersData();
                        break;
                    case 'activations':
                        await loadActivationsData();
                        break;
                    case 'collected-data':
                        await loadCollectedData();
                        break;
                    case 'statistics':
                        await loadStatisticsData();
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
                document.getElementById('collected-members').textContent = data.collected_members;
                
            } catch (error) {
                console.error('載入儀表板數據失敗:', error);
            }
        }
        
        // 載入訂單數據
        async function loadOrdersData() {
            try {
                const response = await fetch('/api/orders');
                const data = await response.json();
                updateOrdersTable(data.orders || []);
            } catch (error) {
                console.error('載入訂單數據失敗:', error);
            }
        }
        
        // 載入激活碼數據
        async function loadActivationsData() {
            try {
                const response = await fetch('/api/activation_codes');
                const data = await response.json();
                updateActivationsTable(data.codes || []);
            } catch (error) {
                console.error('載入激活碼數據失敗:', error);
            }
        }
        
        function updateActivationsTable(codes) {
            const tbody = document.getElementById('activations-tbody');
            tbody.innerHTML = '';
            
            codes.forEach(code => {
                const row = document.createElement('tr');
                
                // 狀態顏色
                const statusClass = code.disabled ? 'text-danger' : (code.used ? 'text-warning' : 'text-success');
                const statusText = code.disabled ? '已停權' : (code.used ? '已使用' : '未使用');
                
                // 方案類型顯示
                const planNames = {
                    'trial': '試用版',
                    'weekly': '週方案',
                    'monthly': '月方案',
                    'premium': '旗艦版'
                };
                const planName = planNames[code.plan_type] || code.plan_type;
                
                row.innerHTML = `
                    <td><code>${code.code}</code></td>
                    <td><span class="badge bg-primary">${planName}</span></td>
                    <td><span class="badge ${code.disabled ? 'bg-danger' : 'bg-success'}">${code.disabled ? '已停權' : '正常'}</span></td>
                    <td>${code.days}天</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td>${code.created_at ? new Date(code.created_at).toLocaleString() : '-'}</td>
                    <td>
                        ${code.disabled ? 
                            `<button class="btn btn-success btn-sm" onclick="enableActivationCode('${code.code}')">恢復</button>` :
                            `<button class="btn btn-danger btn-sm" onclick="disableActivationCode('${code.code}')">停權</button>`
                        }
                        <button class="btn btn-info btn-sm" onclick="viewCodeDetails('${code.code}')">詳情</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
        
        async function disableActivationCode(code) {
            const reason = prompt('請輸入停權原因:', '違規使用');
            if (!reason) return;
            
            try {
                const response = await fetch('/api/disable_activation_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        activation_code: code,
                        reason: reason
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('激活碼已停權');
                    loadActivationsData();
                } else {
                    alert('停權失敗: ' + data.error);
                }
            } catch (error) {
                console.error('停權失敗:', error);
                alert('停權失敗');
            }
        }
        
        async function enableActivationCode(code) {
            if (!confirm('確定要恢復此激活碼嗎？')) return;
            
            try {
                const response = await fetch('/api/enable_activation_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        activation_code: code
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    alert('激活碼已恢復');
                    loadActivationsData();
                } else {
                    alert('恢復失敗: ' + data.error);
                }
            } catch (error) {
                console.error('恢復失敗:', error);
                alert('恢復失敗');
            }
        }
        
        function viewCodeDetails(code) {
            // 這裡可以顯示激活碼的詳細信息
            alert('激活碼詳情功能開發中: ' + code);
        }
        
        function refreshActivations() {
            loadActivationsData();
        }
        
        function searchActivations() {
            const searchTerm = document.getElementById('activation-search').value.toLowerCase();
            const rows = document.querySelectorAll('#activations-tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
        
        // 載入採集數據
        async function loadCollectedData() {
            try {
                const response = await fetch('/api/collected-data');
                const data = await response.json();
                updateCollectedDataTable(data.collected_data || []);
            } catch (error) {
                console.error('載入採集數據失敗:', error);
            }
        }
        
        // 更新訂單表格
        function updateOrdersTable(orders) {
            const tbody = document.getElementById('orders-tbody');
            tbody.innerHTML = '';
            
            orders.forEach(order => {
                const row = `
                    <tr>
                        <td><code>${order.order_id}</code></td>
                        <td>${order.user_id}</td>
                        <td><span class="badge bg-primary">${order.plan_type_chinese}</span></td>
                        <td>${order.amount}</td>
                        <td>${order.currency}</td>
                        <td><span class="badge ${order.status === 'paid' ? 'status-paid' : 'status-pending'}">${order.status === 'paid' ? '已付款' : '待付款'}</span></td>
                        <td><small><code>${order.tx_hash ? order.tx_hash.slice(0, 16) + '...' : 'N/A'}</code></small></td>
                        <td>${new Date(order.created_at).toLocaleDateString('zh-TW')}</td>
                        <td>${new Date(order.expires_at).toLocaleDateString('zh-TW')}</td>
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
                        <td><code>${activation.activation_code}</code></td>
                        <td><span class="badge bg-info">${activation.plan_type_chinese}</span></td>
                        <td>${activation.user_id}</td>
                        <td>${activation.order_id || 'N/A'}</td>
                        <td>${activation.days}</td>
                        <td><span class="badge ${activation.used ? 'status-used' : 'status-active'}">${activation.used ? '已使用' : '未使用'}</span></td>
                        <td>${new Date(activation.created_at).toLocaleDateString('zh-TW')}</td>
                        <td>${new Date(activation.expires_at).toLocaleDateString('zh-TW')}</td>
                        <td>${activation.used_by_device ? activation.used_by_device.slice(0, 12) + '...' : 'N/A'}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 更新採集數據表格
        function updateCollectedDataTable(collectedData) {
            const tbody = document.getElementById('collected-data-tbody');
            tbody.innerHTML = '';
            
            collectedData.forEach(data => {
                const row = `
                    <tr>
                        <td><code>${data.activation_code}</code></td>
                        <td><small>${data.device_info}</small></td>
                        <td>${data.collection_method}</td>
                        <td>${data.target_groups}</td>
                        <td><span class="badge bg-success">${data.total_collected}</span></td>
                        <td>${new Date(data.upload_timestamp).toLocaleDateString('zh-TW')}</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewCollectedDetails('${data.activation_code}')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }
        
        // 按鈕功能
        function refreshOrders() {
            loadOrdersData();
        }
        
        function refreshActivations() {
            loadActivationsData();
        }
        
        function refreshCollectedData() {
            loadCollectedData();
        }
        
        function searchActivations() {
            const searchTerm = document.getElementById('activation-search').value;
            alert('搜索激活碼: ' + searchTerm);
        }
        
        function viewCollectedDetails(activationCode) {
            alert('查看採集詳情: ' + activationCode);
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
    """儀表板API - 整合機器人數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        uploaded_data = get_uploaded_data()
        
        # 計算統計數據
        total_revenue = bot_db.get('statistics', {}).get('total_revenue', 0)
        total_orders = len(bot_db.get('orders', {}))
        total_activations = len(bot_db.get('activation_codes', {}))
        
        # 計算採集成員總數
        collected_members = 0
        for data in uploaded_data:
            if 'collected_members' in data:
                collected_members += len(data['collected_members'])
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'total_activations': total_activations,
            'collected_members': collected_members
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def api_orders():
    """訂單API - 機器人訂單數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        orders = []
        
        for order_id, order_data in bot_db.get('orders', {}).items():
            orders.append({
                'order_id': order_data.get('order_id'),
                'user_id': order_data.get('user_id'),
                'plan_type': order_data.get('plan_type'),
                'plan_type_chinese': get_plan_type_chinese(order_data.get('plan_type')),
                'amount': order_data.get('amount'),
                'currency': order_data.get('currency'),
                'status': order_data.get('status'),
                'tx_hash': order_data.get('tx_hash'),
                'created_at': order_data.get('created_at'),
                'expires_at': order_data.get('expires_at')
            })
        
        # 按創建時間排序
        orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'orders': orders})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activations')
def api_activations():
    """激活碼API - 機器人激活碼數據"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        activations = []
        
        for code, code_data in bot_db.get('activation_codes', {}).items():
            activations.append({
                'activation_code': code_data.get('activation_code'),
                'plan_type': code_data.get('plan_type'),
                'plan_type_chinese': get_plan_type_chinese(code_data.get('plan_type')),
                'user_id': code_data.get('user_id'),
                'order_id': code_data.get('order_id'),
                'days': code_data.get('days'),
                'used': code_data.get('used', False),
                'created_at': code_data.get('created_at'),
                'expires_at': code_data.get('expires_at'),
                'used_by_device': code_data.get('used_by_device')
            })
        
        # 按創建時間排序
        activations.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'activations': activations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/collected-data')
def api_collected_data():
    """採集數據API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        uploaded_data = get_uploaded_data()
        collected_data = []
        
        for data in uploaded_data:
            device_info = data.get('device_info', {})
            collection_info = data.get('collection_info', {})
            
            collected_data.append({
                'activation_code': data.get('activation_code'),
                'device_info': f"{device_info.get('hostname', 'N/A')} ({device_info.get('platform', 'N/A')})",
                'collection_method': collection_info.get('collection_method', 'N/A'),
                'target_groups': ', '.join(collection_info.get('target_groups', [])),
                'total_collected': collection_info.get('total_collected', 0),
                'upload_timestamp': data.get('upload_timestamp')
            })
        
        # 按上傳時間排序
        collected_data.sort(key=lambda x: x['upload_timestamp'], reverse=True)
        
        return jsonify({'collected_data': collected_data})
        
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

@app.route('/api/activation_codes')
def api_activation_codes():
    """獲取激活碼列表API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        bot_db = get_bot_database()
        activation_codes = bot_db.get('activation_codes', {})
        
        # 格式化激活碼列表
        codes_list = []
        for code, info in activation_codes.items():
            codes_list.append({
                'code': code,
                'plan_type': info.get('plan_type', 'unknown'),
                'days': info.get('days', 0),
                'used': info.get('used', False),
                'disabled': info.get('disabled', False),
                'created_at': info.get('created_at', ''),
                'used_at': info.get('used_at', ''),
                'used_by_device': info.get('used_by_device', ''),
                'disabled_at': info.get('disabled_at', ''),
                'disabled_by': info.get('disabled_by', ''),
                'expires_at': info.get('expires_at', '')
            })
        
        # 按創建時間排序
        codes_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'codes': codes_list,
            'total': len(codes_list)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/disable_activation_code', methods=['POST'])
def api_disable_activation_code():
    """停權激活碼API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        activation_code = data.get('activation_code')
        reason = data.get('reason', '管理員停權')
        
        if not activation_code:
            return jsonify({'error': '激活碼不能為空'}), 400
        
        # 使用數據庫適配器獲取激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 使用專門的狀態更新方法
        success = db_adapter.update_activation_code_status(
            activation_code, 
            disabled=True, 
            disabled_by=session.get('username', 'admin'), 
            reason=reason
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'激活碼 {activation_code} 已被停權'
            })
        else:
            return jsonify({'error': '停權失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/enable_activation_code', methods=['POST'])
def api_enable_activation_code():
    """恢復激活碼API"""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        activation_code = data.get('activation_code')
        
        if not activation_code:
            return jsonify({'error': '激活碼不能為空'}), 400
        
        # 使用數據庫適配器獲取激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 使用專門的狀態更新方法
        success = db_adapter.update_activation_code_status(
            activation_code, 
            disabled=False, 
            disabled_by=session.get('username', 'admin'), 
            reason=None
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'激活碼 {activation_code} 已恢復'
            })
        else:
            return jsonify({'error': '恢復失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_software_data', methods=['POST'])
def api_upload_software_data():
    """接收軟件上傳的數據API"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({'error': '無效的API密鑰'}), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id')
        software_data = data.get('data', {})
        
        if not activation_code or not device_id:
            return jsonify({'error': '缺少必要參數'}), 400
        
        # 驗證激活碼
        code_info = db_adapter.get_activation_code(activation_code)
        if not code_info:
            return jsonify({'error': '激活碼不存在'}), 404
        
        # 檢查是否被停權
        if code_info.get('disabled', False):
            return jsonify({'error': '激活碼已被停權，軟件已停止'}), 403
        
        # 保存軟件數據
        software_record = {
            'activation_code': activation_code,
            'device_id': device_id,
            'upload_time': datetime.now().isoformat(),
            'accounts': software_data.get('accounts', []),
            'collections': software_data.get('collections', []),
            'invitations': software_data.get('invitations', []),
            'statistics': software_data.get('statistics', {}),
            'status': software_data.get('status', 'running')
        }
        
        # 保存到上傳數據目錄
        upload_file = os.path.join(UPLOAD_DATA_DIR, f"software_{device_id}_{int(datetime.now().timestamp())}.json")
        os.makedirs(UPLOAD_DATA_DIR, exist_ok=True)
        
        with open(upload_file, 'w', encoding='utf-8') as f:
            json.dump(software_record, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '數據上傳成功',
            'activation_status': 'active' if not code_info.get('disabled', False) else 'disabled'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# ========== API端點：供TG旺軟件使用 ==========

@app.route('/api/health', methods=['GET'])
def api_health():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "TG旺企業管理系統"
    })

@app.route('/api/verify_activation', methods=['POST'])
def api_verify_activation():
    """API: 驗證激活碼"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "valid": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id', 'unknown')
        
        if not activation_code:
            return jsonify({
                "valid": False,
                "message": "缺少激活碼"
            }), 400
        
        # 讀取機器人數據庫
        bot_data = get_bot_database()
        code_info = bot_data.get('activation_codes', {}).get(activation_code)
        
        if not code_info:
            return jsonify({
                "valid": False,
                "message": "激活碼不存在"
            })
        
        # 檢查是否被停權
        if code_info.get('disabled', False):
            return jsonify({
                "valid": False,
                "message": f"激活碼已被停權，停權時間: {code_info.get('disabled_at', 'unknown')}，原因: {code_info.get('disabled_reason', '管理員停權')}"
            })
        
        if code_info.get('used', False):
            return jsonify({
                "valid": False,
                "message": f"激活碼已於 {code_info.get('used_at', 'unknown')} 使用過"
            })
        
        # 檢查是否過期
        expires_at = datetime.fromisoformat(code_info['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({
                "valid": False,
                "message": f"激活碼已於 {expires_at.strftime('%Y-%m-%d %H:%M:%S')} 過期"
            })
        
        # 激活碼有效
        return jsonify({
            "valid": True,
            "message": "激活碼有效",
            "data": {
                "plan_type": code_info['plan_type'],
                "days": code_info['days'],
                "expires_at": code_info['expires_at'],
                "created_at": code_info['created_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            "valid": False,
            "message": f"驗證錯誤: {str(e)}"
        }), 500

@app.route('/api/use_activation', methods=['POST'])
def api_use_activation():
    """API: 使用激活碼（標記為已使用）"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "success": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        device_id = data.get('device_id', 'unknown')
        
        if not activation_code:
            return jsonify({
                "success": False,
                "message": "缺少激活碼"
            }), 400
        
        # 讀取機器人數據庫
        bot_data = get_bot_database()
        code_info = bot_data.get('activation_codes', {}).get(activation_code)
        
        if not code_info:
            return jsonify({
                "success": False,
                "message": "激活碼不存在"
            })
        
        if code_info.get('used', False):
            return jsonify({
                "success": False,
                "message": "激活碼已使用過"
            })
        
        # 標記為已使用
        code_info['used'] = True
        code_info['used_at'] = datetime.now().isoformat()
        code_info['used_by_device'] = device_id
        
        # 保存到數據庫
        with open(BOT_DATABASE_PATH, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": f"激活成功 - {code_info['plan_type']} ({code_info['days']}天)",
            "data": {
                "plan_type": code_info['plan_type'],
                "days": code_info['days'],
                "expires_at": code_info['expires_at'],
                "used_at": code_info['used_at'],
                "device_id": device_id
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"使用錯誤: {str(e)}"
        }), 500

@app.route('/api/activation_codes', methods=['GET'])
def api_get_activation_codes():
    """API: 獲取所有激活碼"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "success": False,
                "message": "無效的API密鑰"
            }), 401
        
        bot_data = get_bot_database()
        activation_codes = bot_data.get('activation_codes', {})
        
        # 格式化激活碼列表
        codes_list = []
        for code, info in activation_codes.items():
            codes_list.append({
                "activation_code": code,
                "plan_type": info['plan_type'],
                "days": info['days'],
                "created_at": info['created_at'],
                "expires_at": info['expires_at'],
                "used": info.get('used', False),
                "used_at": info.get('used_at'),
                "user_id": info.get('user_id')
            })
        
        return jsonify({
            "success": True,
            "total": len(codes_list),
            "codes": codes_list
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"獲取錯誤: {str(e)}"
        }), 500

@app.route('/sync/activation_code', methods=['POST'])
def sync_activation_code():
    """同步激活碼端點 - 供機器人雲端同步使用"""
    try:
        # 檢查API密鑰
        api_key = request.headers.get('X-API-Key')
        if api_key != "tg-api-secure-key-2024":
            return jsonify({
                "success": False,
                "message": "無效的API密鑰"
            }), 401
        
        data = request.get_json()
        activation_code = data.get('activation_code')
        code_data = data.get('code_data')
        
        if not activation_code or not code_data:
            return jsonify({
                "success": False,
                "message": "數據不完整"
            }), 400
        
        # 使用數據庫適配器保存激活碼
        success = db_adapter.save_activation_code(activation_code, code_data)
        
        # 同時更新本地JSON文件（向後兼容）
        try:
            bot_data = get_bot_database()
            bot_data['activation_codes'][activation_code] = code_data
            
            # 更新統計
            if 'statistics' not in bot_data:
                bot_data['statistics'] = {}
            if 'activations_generated' not in bot_data['statistics']:
                bot_data['statistics']['activations_generated'] = 0
            
            bot_data['statistics']['activations_generated'] = len(bot_data['activation_codes'])
            
            # 保存到本地JSON文件
            with open(BOT_DATABASE_PATH, 'w', encoding='utf-8') as f:
                json.dump(bot_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"本地JSON保存失敗: {e}")
        
        if success:
            return jsonify({
                "success": True,
                "message": f"激活碼 {activation_code} 同步成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"激活碼 {activation_code} 同步失敗"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"同步錯誤: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🚀 TG旺企業管理系統 - 機器人數據整合版")
    print("=" * 60)
    print("🔗 已整合TG機器人數據:")
    print("   ✅ 機器人訂單數據")
    print("   ✅ 激活碼管理")
    print("   ✅ 用戶採集數據")
    print("   ✅ 實時統計分析")
    print("=" * 60)
    print("📊 數據來源:")
    print(f"   📄 機器人數據庫: {BOT_DATABASE_PATH}")
    print(f"   📁 採集數據目錄: {UPLOAD_DATA_DIR}")
    print("=" * 60)
    print("📌 預設帳號:")
    print(f"   admin/{ADMIN_PASSWORD} (超級管理員)")
    print(f"   manager/{MANAGER_PASSWORD} (業務經理)")
    print(f"   agent/{AGENT_PASSWORD} (代理商)")
    print("=" * 60)
    
    # 獲取端口
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)