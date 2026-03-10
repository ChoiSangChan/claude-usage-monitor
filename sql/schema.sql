-- Claude Usage Monitor Database Schema

-- API 호출 기록 테이블
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,              -- 'anthropic' | 'openai'
    model TEXT NOT NULL,                 -- 모델명 (e.g. 'claude-opus-4-6')
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,  -- 계산된 비용 (USD)
    session_id TEXT DEFAULT '',          -- 세션 식별자
    metadata TEXT,                       -- JSON 추가 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 설정 테이블
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 설정값 삽입
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('monthly_budget_usd', '100.00'),
    ('alert_threshold_percent', '80'),
    ('currency', 'USD'),
    ('theme', 'auto');

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_prompts_provider ON prompts(provider);
CREATE INDEX IF NOT EXISTS idx_prompts_session_id ON prompts(session_id);
