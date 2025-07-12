#!/usr/bin/env python3
"""
測試integrated_enterprise_app.py的模板是否有語法錯誤
"""

import sys
sys.path.append('.')

from integrated_enterprise_app import DASHBOARD_TEMPLATE

# 測試渲染模板
try:
    # 模擬session數據
    test_data = {
        'username': 'admin',
        'user_permissions': {'all'},
    }
    
    # 嘗試渲染模板
    from jinja2 import Template
    template = Template(DASHBOARD_TEMPLATE)
    
    # 渲染並輸出前1000個字符和第760-780行
    rendered = template.render(**test_data)
    
    lines = rendered.split('\n')
    print(f"總行數: {len(lines)}")
    
    # 找出第771行附近的內容
    print("\n第765-785行的內容：")
    for i in range(max(0, 764), min(len(lines), 785)):
        line = lines[i]
        # 檢查特殊字符
        if i == 770:  # 第771行
            print(f"\n=== 第{i+1}行 ===")
            print(f"內容: {repr(line)}")
            print(f"長度: {len(line)}")
            if line:
                print(f"第52個字符: {repr(line[51] if len(line) > 51 else 'N/A')}")
            print("===\n")
        else:
            print(f"{i+1}: {line[:100]}...")
            
except Exception as e:
    print(f"錯誤: {e}")
    import traceback
    traceback.print_exc()