#!/usr/bin/env python3
"""
全面檢查JavaScript語法問題
"""

import re

# 讀取文件
with open('integrated_enterprise_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找出DASHBOARD_TEMPLATE部分
dashboard_match = re.search(r"DASHBOARD_TEMPLATE = '''(.*?)'''\s*\n\s*# API路由", content, re.DOTALL)
if dashboard_match:
    template = dashboard_match.group(1)
    
    # 檢查所有的<script>標籤內容
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', template, re.DOTALL)
    
    print(f"找到 {len(script_matches)} 個script標籤")
    
    for i, script in enumerate(script_matches):
        print(f"\n=== Script {i+1} ===")
        lines = script.split('\n')
        
        # 檢查每一行
        for j, line in enumerate(lines):
            # 跳過空行和註釋
            if not line.strip() or line.strip().startswith('//'):
                continue
                
            # 檢查未閉合的字符串
            # 計算引號數量（排除轉義的引號）
            single_quotes = len(re.findall(r"(?<!\\)'", line))
            double_quotes = len(re.findall(r'(?<!\\)"', line))
            backticks = line.count('`')
            
            # 檢查模板字符串中的嵌套
            if '${' in line and backticks % 2 == 0:
                print(f"行 {j+1}: 可能的模板字符串錯誤 - ${{}}")
                print(f"  內容: {line.strip()[:80]}...")
            
            # 檢查函數重複定義
            func_match = re.match(r'\s*function\s+(\w+)', line)
            if func_match:
                func_name = func_match.group(1)
                # 計算這個函數名出現的次數
                func_count = len(re.findall(rf'function\s+{func_name}\s*\(', script))
                if func_count > 1:
                    print(f"行 {j+1}: 函數 '{func_name}' 可能重複定義")

# 特別檢查switchTab是否定義
if 'function switchTab' in content:
    print("\n✓ switchTab 函數已定義")
else:
    print("\n✗ switchTab 函數未找到！")

# 檢查所有onclick中調用的函數是否都有定義
onclick_funcs = re.findall(r'onclick="([^"(]+)\(', content)
onclick_funcs.extend(re.findall(r"onclick='([^'(]+)\(", content))
onclick_funcs = list(set(onclick_funcs))

print(f"\n發現 {len(onclick_funcs)} 個onclick函數調用:")
for func in onclick_funcs:
    if f'function {func}' in content:
        print(f"  ✓ {func}")
    else:
        print(f"  ✗ {func} - 未定義！")