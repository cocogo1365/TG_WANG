#!/usr/bin/env python3
"""
修復 activation_codes 表結構
添加停權相關欄位
"""
import psycopg2

# PostgreSQL 連接
DATABASE_URL = "postgresql://postgres:KJuMwmpKTPLNteUICkjMoNslsvwxodHa@interchange.proxy.rlwy.net:12086/railway"

def check_table_structure():
    """檢查表結構"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 檢查現有欄位
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'activation_codes'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("=== 現有欄位 ===")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
        
        cur.close()
        conn.close()
        
        return [col[0] for col in columns]
        
    except Exception as e:
        print(f"錯誤: {e}")
        return []

def add_missing_columns():
    """添加缺少的欄位"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 需要的欄位
        required_columns = {
            'disabled': 'BOOLEAN DEFAULT FALSE',
            'disabled_at': 'TIMESTAMP',
            'disabled_by': 'VARCHAR(100)',
            'disabled_reason': 'TEXT'
        }
        
        # 檢查並添加缺少的欄位
        for column, data_type in required_columns.items():
            try:
                cur.execute(f"""
                    ALTER TABLE activation_codes 
                    ADD COLUMN IF NOT EXISTS {column} {data_type}
                """)
                print(f"✓ 添加欄位: {column} {data_type}")
            except Exception as e:
                print(f"✗ 添加欄位 {column} 失敗: {e}")
        
        # 創建索引
        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_activation_codes_disabled 
                ON activation_codes(disabled)
            """)
            print("✓ 創建索引: idx_activation_codes_disabled")
        except Exception as e:
            print(f"✗ 創建索引失敗: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n✅ 表結構修復完成！")
        
    except Exception as e:
        print(f"錯誤: {e}")

def test_disable_function():
    """測試停權功能"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 測試更新語句
        test_code = 'TEST_CODE_123'
        
        # 先插入測試激活碼
        cur.execute("""
            INSERT INTO activation_codes (code, plan_type, days, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (code) DO NOTHING
        """, (test_code, 'test', 30))
        
        # 測試停權
        cur.execute("""
            UPDATE activation_codes 
            SET disabled = TRUE, 
                disabled_at = CURRENT_TIMESTAMP, 
                disabled_by = 'test_admin', 
                disabled_reason = '測試停權'
            WHERE code = %s
        """, (test_code,))
        
        # 驗證結果
        cur.execute("""
            SELECT code, disabled, disabled_at, disabled_by, disabled_reason
            FROM activation_codes 
            WHERE code = %s
        """, (test_code,))
        
        result = cur.fetchone()
        if result:
            print("\n=== 測試停權功能 ===")
            print(f"激活碼: {result[0]}")
            print(f"已停權: {result[1]}")
            print(f"停權時間: {result[2]}")
            print(f"停權者: {result[3]}")
            print(f"停權原因: {result[4]}")
            print("✅ 停權功能測試成功！")
        
        # 清理測試數據
        cur.execute("DELETE FROM activation_codes WHERE code = %s", (test_code,))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"測試失敗: {e}")

if __name__ == "__main__":
    print("=== 修復 activation_codes 表結構 ===\n")
    
    # 步驟1：檢查現有結構
    print("步驟1：檢查現有表結構")
    existing_columns = check_table_structure()
    
    # 步驟2：添加缺少的欄位
    print("\n步驟2：添加缺少的欄位")
    add_missing_columns()
    
    # 步驟3：再次檢查
    print("\n步驟3：驗證修復結果")
    check_table_structure()
    
    # 步驟4：測試功能
    print("\n步驟4：測試停權功能")
    test_disable_function()