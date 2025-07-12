-- 創建採集數據表
CREATE TABLE IF NOT EXISTS collection_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info JSONB,
    ip_location JSONB,
    group_name VARCHAR(255),
    group_link TEXT,
    collection_method VARCHAR(100) DEFAULT '活躍用戶採集',
    members_count INTEGER DEFAULT 0,
    members_data JSONB,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引以提高查詢性能
CREATE INDEX IF NOT EXISTS idx_collection_activation_code ON collection_data(activation_code);
CREATE INDEX IF NOT EXISTS idx_collection_upload_time ON collection_data(upload_time DESC);
CREATE INDEX IF NOT EXISTS idx_collection_device_id ON collection_data(device_id);

-- 創建軟件數據表（如果需要）
CREATE TABLE IF NOT EXISTS software_data (
    id SERIAL PRIMARY KEY,
    activation_code VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    device_info JSONB,
    ip_location JSONB,
    accounts JSONB,
    collections JSONB,
    invitations JSONB,
    statistics JSONB,
    status VARCHAR(50),
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_software_activation_code ON software_data(activation_code);
CREATE INDEX IF NOT EXISTS idx_software_device_id ON software_data(device_id);

-- 檢查現有表
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 檢查激活碼表結構
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'activation_codes'
ORDER BY ordinal_position;