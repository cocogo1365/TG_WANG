#!/usr/bin/env python3
"""
修復integrated_enterprise_app.py中的JavaScript語法問題
"""

import re

# 讀取文件
with open('integrated_enterprise_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找DASHBOARD_TEMPLATE的起始和結束位置
start_match = re.search(r"DASHBOARD_TEMPLATE = '''", content)
end_match = re.search(r"'''\n# API路由", content)

if start_match and end_match:
    # 提取模板內容
    template_start = start_match.end()
    template_end = end_match.start()
    template_content = content[template_start:template_end]
    
    # 檢查是否有未轉義的三引號
    if "'''" in template_content:
        print("警告：模板中發現未轉義的三引號！")
        # 替換為轉義的引號
        template_content = template_content.replace("'''", "\\'\\'\\'")
    
    # 檢查是否有Python f-string語法（在普通字符串中不應該有）
    if re.search(r'(?<!`)f"[^"]*"', template_content):
        print("警告：發現可能的f-string語法錯誤！")
    
    # 查找並報告潛在的問題行
    lines = template_content.split('\n')
    for i, line in enumerate(lines, start=1):
        line_no = i + content[:template_start].count('\n')
        
        # 檢查是否有未閉合的字符串
        if line.count('"') % 2 != 0 and '//' not in line:
            print(f"第{line_no}行可能有未閉合的雙引號: {line.strip()[:50]}...")
        
        if line.count("'") % 2 != 0 and '//' not in line and '&#39;' not in line:
            print(f"第{line_no}行可能有未閉合的單引號: {line.strip()[:50]}...")
        
        # 檢查是否有錯誤的模板字符串語法
        if '${' in line and '`' not in line:
            print(f"第{line_no}行：在非模板字符串中使用了${{}}: {line.strip()[:50]}...")

print("\n掃描完成！")

# 輸出第771行附近的內容進行檢查
print("\n第771行附近的內容：")
lines = content.split('\n')
for i in range(max(0, 770-5), min(len(lines), 771+5)):
    print(f"{i+1}: {lines[i]}")