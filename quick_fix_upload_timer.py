#!/usr/bin/env python3
"""
快速定位並修復測試5.py的持續上傳問題
"""
import os
import re

def find_timer_code(file_path):
    """查找定時器相關代碼"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # 搜索模式
    patterns = [
        r'sleep\s*\(\s*300\s*\)',  # sleep(300)
        r'sleep\s*\(\s*5\s*\*\s*60\s*\)',  # sleep(5*60)
        r'Timer\s*\(',  # Timer(
        r'while\s+True\s*:',  # while True:
        r'schedule\.',  # schedule.
        r'start_auto_upload',  # 自動上傳函數
        r'background.*upload',  # 後台上傳
        r'daemon\s*=\s*True',  # 守護線程
    ]
    
    print(f"\n=== 掃描文件: {file_path} ===")
    found = False
    
    for i, line in enumerate(lines, 1):
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                print(f"第 {i} 行: {line.strip()}")
                # 顯示上下文
                start = max(0, i-3)
                end = min(len(lines), i+2)
                print("上下文:")
                for j in range(start, end):
                    prefix = ">>> " if j == i-1 else "    "
                    print(f"{prefix}{j+1}: {lines[j]}")
                print("-" * 50)
                found = True
    
    if not found:
        print("未找到明顯的定時器代碼")

# 掃描可能的文件位置
possible_files = [
    r"C:\Users\XX11\PythonProject6\TG-旺\working_release\測試5.py",
    r"C:\Users\XX11\PythonProject6\TG-旺\working_release\software_data_uploader.py",
    r"C:\Users\XX11\PythonProject6\TG-旺\working_release\雲端數據上傳系統.py",
]

print("=== 測試5.py 持續上傳問題診斷 ===")
print("\n正在搜索定時上傳相關代碼...")

for file_path in possible_files:
    if os.path.exists(file_path):
        find_timer_code(file_path)
    else:
        print(f"\n文件不存在: {file_path}")

print("\n=== 修復建議 ===")
print("1. 找到包含 sleep(300) 或 Timer 的代碼")
print("2. 註釋掉自動上傳的循環或定時器")
print("3. 確保上傳只在手動操作時觸發")
print("4. 重新啟動測試5.py")