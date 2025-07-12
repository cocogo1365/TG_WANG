-- TG_WANG 數據庫設置
-- 創建採集數據相關的表
-- 日期：2025-01-12

-- ========================================
-- 1. 創建 collection_data 表（採集數據）
-- ========================================
DROP TABLE IF EXISTS collection_data CASCADE;

CREATE TABLE collection_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info TEXT,
    ip_location TEXT,
    group_name VARCHAR(255),
    group_link TEXT,
    collection_method VARCHAR(100) DEFAULT '活躍用戶採集',
    members_count INTEGER DEFAULT 0,
    members_data TEXT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引以提高查詢性能
CREATE INDEX idx_collection_activation_code ON collection_data(activation_code);
CREATE INDEX idx_collection_upload_time ON collection_data(upload_time DESC);
CREATE INDEX idx_collection_device_id ON collection_data(device_id);

-- 添加註釋
COMMENT ON TABLE collection_data IS '採集數據表，存儲軟體上傳的群組成員數據';
COMMENT ON COLUMN collection_data.activation_code IS '激活碼';
COMMENT ON COLUMN collection_data.device_id IS '設備ID';
COMMENT ON COLUMN collection_data.device_info IS '設備信息（JSON格式）';
COMMENT ON COLUMN collection_data.ip_location IS 'IP位置信息（JSON格式）';
COMMENT ON COLUMN collection_data.group_name IS '群組名稱';
COMMENT ON COLUMN collection_data.group_link IS '群組鏈接';
COMMENT ON COLUMN collection_data.collection_method IS '採集方法';
COMMENT ON COLUMN collection_data.members_count IS '成員數量';
COMMENT ON COLUMN collection_data.members_data IS '成員數據（JSON格式）';

-- ========================================
-- 2. 創建 software_data 表（軟體數據）
-- ========================================
DROP TABLE IF EXISTS software_data CASCADE;

CREATE TABLE software_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info TEXT,
    ip_location TEXT,
    accounts TEXT,
    collections TEXT,
    invitations TEXT,
    statistics TEXT,
    status VARCHAR(50),
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX idx_software_activation_code ON software_data(activation_code);
CREATE INDEX idx_software_device_id ON software_data(device_id);
CREATE INDEX idx_software_upload_time ON software_data(upload_time DESC);

-- 添加註釋
COMMENT ON TABLE software_data IS '軟體數據表，存儲完整的軟體運行數據';
COMMENT ON COLUMN software_data.accounts IS '帳號信息（JSON格式）';
COMMENT ON COLUMN software_data.collections IS '採集記錄（JSON格式）';
COMMENT ON COLUMN software_data.invitations IS '邀請記錄（JSON格式）';
COMMENT ON COLUMN software_data.statistics IS '統計數據（JSON格式）';

-- ========================================
-- 3. 測試數據（可選）
-- ========================================
-- 插入測試數據以驗證表結構
INSERT INTO collection_data 
(activation_code, device_id, device_info, group_name, group_link, members_count, members_data)
VALUES 
(
    'TEST_CODE', 
    'test_device_001',
    '{"hostname": "TestPC", "platform": "Windows"}',
    '測試群組',
    'https://t.me/test_group',
    2,
    '[{"id": 1, "username": "test1", "first_name": "測試用戶1"}, {"id": 2, "username": "test2", "first_name": "測試用戶2"}]'
);

-- ========================================
-- 4. 驗證表創建
-- ========================================
-- 列出所有表
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 檢查 collection_data 表結構
SELECT 
    column_name AS "欄位名稱",
    data_type AS "資料類型",
    character_maximum_length AS "最大長度",
    column_default AS "預設值",
    is_nullable AS "允許空值"
FROM information_schema.columns
WHERE table_name = 'collection_data'
ORDER BY ordinal_position;

-- 檢查測試數據
SELECT * FROM collection_data LIMIT 10;

-- ========================================
-- 5. 授權（如果需要）
-- ========================================
-- GRANT ALL PRIVILEGES ON TABLE collection_data TO postgres;
-- GRANT ALL PRIVILEGES ON TABLE software_data TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ========================================
-- 完成提示
-- ========================================
-- 執行完成後，你應該看到：
-- 1. 兩個新表：collection_data 和 software_data
-- 2. 相關的索引已創建
-- 3. 一條測試數據在 collection_data 表中