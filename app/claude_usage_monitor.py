#!/usr/bin/env python3
"""
Claude Usage Monitor - Standalone macOS Menu Bar App
rumps 기반 독립 실행형 메뉴바 앱. 10분마다 사용량을 자동 갱신합니다.
"""

import sqlite3
import os
import threading
from datetime import datetime
from pathlib import Path

import rumps

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
APP_NAME = "Claude Usage Monitor"
REFRESH_INTERVAL_SEC = 600  # 10분 (초)
DB_PATH = Path.home() / ".claude-usage-monitor" / "usage.db"

# ─────────────────────────────────────────────
# 35개 모델 가격표 (USD per 1M tokens)
# ─────────────────────────────────────────────
PRICING = {
    # Anthropic
    "claude-opus-4-6":              {"input": 15.00,  "output": 75.00,  "provider": "Anthropic"},
    "claude-sonnet-4-6":            {"input": 3.00,   "output": 15.00,  "provider": "Anthropic"},
    "claude-haiku-4-5-20251001":    {"input": 0.80,   "output": 4.00,   "provider": "Anthropic"},
    "claude-3-5-sonnet-20241022":   {"input": 3.00,   "output": 15.00,  "provider": "Anthropic"},
    "claude-3-5-haiku-20241022":    {"input": 0.80,   "output": 4.00,   "provider": "Anthropic"},
    "claude-3-opus-20240229":       {"input": 15.00,  "output": 75.00,  "provider": "Anthropic"},
    "claude-3-sonnet-20240229":     {"input": 3.00,   "output": 15.00,  "provider": "Anthropic"},
    "claude-3-haiku-20240307":      {"input": 0.25,   "output": 1.25,   "provider": "Anthropic"},
    # OpenAI - GPT-4o family
    "gpt-4o":                       {"input": 2.50,   "output": 10.00,  "provider": "OpenAI"},
    "gpt-4o-2024-11-20":            {"input": 2.50,   "output": 10.00,  "provider": "OpenAI"},
    "gpt-4o-2024-08-06":            {"input": 2.50,   "output": 10.00,  "provider": "OpenAI"},
    "gpt-4o-2024-05-13":            {"input": 5.00,   "output": 15.00,  "provider": "OpenAI"},
    "gpt-4o-mini":                  {"input": 0.15,   "output": 0.60,   "provider": "OpenAI"},
    "gpt-4o-mini-2024-07-18":       {"input": 0.15,   "output": 0.60,   "provider": "OpenAI"},
    # OpenAI - GPT-4 family
    "gpt-4-turbo":                  {"input": 10.00,  "output": 30.00,  "provider": "OpenAI"},
    "gpt-4-turbo-2024-04-09":       {"input": 10.00,  "output": 30.00,  "provider": "OpenAI"},
    "gpt-4":                        {"input": 30.00,  "output": 60.00,  "provider": "OpenAI"},
    "gpt-4-0613":                   {"input": 30.00,  "output": 60.00,  "provider": "OpenAI"},
    "gpt-4-32k":                    {"input": 60.00,  "output": 120.00, "provider": "OpenAI"},
    # OpenAI - GPT-3.5 family
    "gpt-3.5-turbo":                {"input": 0.50,   "output": 1.50,   "provider": "OpenAI"},
    "gpt-3.5-turbo-0125":           {"input": 0.50,   "output": 1.50,   "provider": "OpenAI"},
    "gpt-3.5-turbo-1106":           {"input": 1.00,   "output": 2.00,   "provider": "OpenAI"},
    # OpenAI - o1/o3 reasoning
    "o1":                           {"input": 15.00,  "output": 60.00,  "provider": "OpenAI"},
    "o1-preview":                   {"input": 15.00,  "output": 60.00,  "provider": "OpenAI"},
    "o1-mini":                      {"input": 3.00,   "output": 12.00,  "provider": "OpenAI"},
    "o3":                           {"input": 10.00,  "output": 40.00,  "provider": "OpenAI"},
    "o3-mini":                      {"input": 1.10,   "output": 4.40,   "provider": "OpenAI"},
    # Google
    "gemini-2.0-flash":             {"input": 0.10,   "output": 0.40,   "provider": "Google"},
    "gemini-2.0-pro":               {"input": 1.25,   "output": 10.00,  "provider": "Google"},
    "gemini-1.5-pro":               {"input": 1.25,   "output": 5.00,   "provider": "Google"},
    "gemini-1.5-flash":             {"input": 0.075,  "output": 0.30,   "provider": "Google"},
    # Meta (via API providers)
    "llama-3.1-405b":               {"input": 3.00,   "output": 3.00,   "provider": "Meta"},
    "llama-3.1-70b":                {"input": 0.80,   "output": 0.80,   "provider": "Meta"},
    "llama-3.1-8b":                 {"input": 0.10,   "output": 0.10,   "provider": "Meta"},
    # Mistral
    "mistral-large-latest":         {"input": 2.00,   "output": 6.00,   "provider": "Mistral"},
}


# ─────────────────────────────────────────────
# DB 헬퍼
# ─────────────────────────────────────────────
def get_db():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(str(DB_PATH))


def get_monthly_usage():
    conn = get_db()
    if not conn:
        return 0.0, []
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    cursor = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM prompts WHERE created_at >= ?",
        (month_start,),
    )
    total_cost = cursor.fetchone()[0]
    cursor = conn.execute(
        """
        SELECT provider, model,
               SUM(input_tokens) as input_tokens,
               SUM(output_tokens) as output_tokens,
               SUM(cost_usd) as cost,
               COUNT(*) as calls
        FROM prompts
        WHERE created_at >= ?
        GROUP BY provider, model
        ORDER BY cost DESC
        """,
        (month_start,),
    )
    model_details = cursor.fetchall()
    conn.close()
    return total_cost, model_details


def get_today_usage():
    conn = get_db()
    if not conn:
        return 0.0
    cursor = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM prompts WHERE date(created_at) = date('now')"
    )
    cost = cursor.fetchone()[0]
    conn.close()
    return cost


def get_monthly_budget():
    conn = get_db()
    if not conn:
        return 200.0
    cursor = conn.execute(
        "SELECT value FROM settings WHERE key = 'monthly_budget_usd'"
    )
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 200.0


def set_monthly_budget(value):
    conn = get_db()
    if not conn:
        return
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('monthly_budget_usd', ?, CURRENT_TIMESTAMP)",
        (str(value),),
    )
    conn.commit()
    conn.close()


def format_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_bar_color_name(ratio):
    if ratio < 0.5:
        return "green"
    elif ratio < 0.8:
        return "orange"
    else:
        return "red"


def make_progress_bar(ratio, length=20):
    filled = int(length * min(ratio, 1.0))
    empty = length - filled
    return "\u2588" * filled + "\u2591" * empty


# ─────────────────────────────────────────────
# macOS Menu Bar App
# ─────────────────────────────────────────────
class ClaudeUsageMonitorApp(rumps.App):
    def __init__(self):
        super().__init__(
            APP_NAME,
            title="\U0001F4AC $0/0",
            quit_button=rumps.MenuItem("종료", key="q"),
        )
        self._build_menu()
        self._refresh_data(None)

    def _build_menu(self):
        self.menu = [
            rumps.MenuItem("summary_header", callback=None),
            rumps.MenuItem("month_cost", callback=None),
            rumps.MenuItem("today_cost", callback=None),
            None,  # separator
            rumps.MenuItem("progress_bar", callback=None),
            None,
            rumps.MenuItem("model_section_header", callback=None),
            # model details are added dynamically
            None,
            rumps.MenuItem("pricing_menu"),
            None,
            rumps.MenuItem("settings_menu"),
            None,
            rumps.MenuItem("\U0001F504 새로고침 (10분 자동)", callback=self._refresh_data, key="r"),
        ]
        self._build_pricing_submenu()
        self._build_settings_submenu()

    def _build_pricing_submenu(self):
        pricing_menu = self.menu["pricing_menu"]
        pricing_menu.title = "\U0001F4B5 모델 가격표 (per 1M tokens)"

        providers = {}
        for model_name, info in sorted(PRICING.items(), key=lambda x: (x[1]["provider"], x[0])):
            provider = info["provider"]
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((model_name, info))

        for provider, models in sorted(providers.items()):
            provider_item = rumps.MenuItem(f"\U0001F4E6 {provider}")
            for model_name, info in models:
                model_item = rumps.MenuItem(
                    f"  {model_name}  |  In: ${info['input']:.2f}  Out: ${info['output']:.2f}"
                )
                provider_item.add(model_item)
            pricing_menu.add(provider_item)

    def _build_settings_submenu(self):
        settings_menu = self.menu["settings_menu"]
        settings_menu.title = "\u2699\uFE0F 설정"

        settings_menu.add(rumps.MenuItem(
            f"DB: {DB_PATH}", callback=None
        ))
        settings_menu.add(rumps.MenuItem(
            "\U0001F4C2 DB 폴더 열기", callback=self._open_db_folder
        ))
        settings_menu.add(None)  # separator
        settings_menu.add(rumps.MenuItem(
            "\U0001F4B0 월 예산 변경...", callback=self._change_budget
        ))
        settings_menu.add(None)
        settings_menu.add(rumps.MenuItem(
            "\u23F1 갱신 주기: 10분", callback=None
        ))

    # ─────────────────────────────────────────
    # Timer: 10분마다 자동 갱신
    # ─────────────────────────────────────────
    @rumps.timer(REFRESH_INTERVAL_SEC)
    def _auto_refresh(self, _):
        self._refresh_data(None)

    # ─────────────────────────────────────────
    # 데이터 갱신
    # ─────────────────────────────────────────
    def _refresh_data(self, _):
        monthly_cost, model_details = get_monthly_usage()
        today_cost = get_today_usage()
        budget = get_monthly_budget()
        ratio = monthly_cost / budget if budget > 0 else 0

        # 메뉴바 타이틀 업데이트
        self.title = f"\U0001F4AC ${monthly_cost:.0f}/${budget:.0f}"

        # 요약 섹션
        now = datetime.now()
        self.menu["summary_header"].title = f"\U0001F4CA {now.strftime('%Y년 %m월')} 사용량"
        self.menu["month_cost"].title = (
            f"  이번 달: ${monthly_cost:.2f} / ${budget:.2f} ({ratio * 100:.1f}%)"
        )
        self.menu["today_cost"].title = f"  오늘: ${today_cost:.2f}"

        # 프로그레스 바
        bar = make_progress_bar(ratio)
        self.menu["progress_bar"].title = f"  [{bar}] {ratio * 100:.1f}%"

        # 모델별 상세 (동적 갱신)
        self._update_model_details(model_details, budget)

        # 마지막 갱신 시각
        refresh_time = now.strftime("%H:%M:%S")
        self.menu["\U0001F504 새로고침 (10분 자동)"].title = (
            f"\U0001F504 새로고침 (마지막: {refresh_time})"
        )

    def _update_model_details(self, model_details, budget):
        header = self.menu["model_section_header"]
        # 기존 동적 항목 제거
        keys_to_remove = [
            k for k in self.menu.keys()
            if isinstance(k, str) and k.startswith("_dyn_")
        ]
        for k in keys_to_remove:
            del self.menu[k]

        if not model_details:
            header.title = "\U0001F4ED 이번 달 사용 기록이 없습니다."
            return

        header.title = "\U0001F916 모델별 사용량"

        # Provider별 그룹핑
        providers = {}
        for provider, model, input_t, output_t, cost, calls in model_details:
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((model, input_t, output_t, cost, calls))

        idx = 0
        for provider, models in sorted(providers.items()):
            provider_cost = sum(m[3] for m in models)
            provider_item = rumps.MenuItem(
                f"  \U0001F4E6 {provider.upper()} (${provider_cost:.2f})"
            )

            for model, input_t, output_t, cost, calls in models:
                model_item = rumps.MenuItem(f"    {model}")
                detail = rumps.MenuItem(
                    f"      호출: {calls}회 | In: {format_tokens(input_t)} | Out: {format_tokens(output_t)} | ${cost:.4f}"
                )
                model_item.add(detail)
                provider_item.add(model_item)

            key = f"_dyn_{idx:03d}_{provider}"
            self.menu.insert_after("model_section_header", rumps.MenuItem(key))
            self.menu[key] = provider_item
            self.menu[key].title = provider_item.title
            idx += 1

    # ─────────────────────────────────────────
    # 액션
    # ─────────────────────────────────────────
    def _open_db_folder(self, _):
        os.system(f'open "{DB_PATH.parent}"')

    def _change_budget(self, _):
        response = rumps.Window(
            title="월 예산 변경",
            message="새 월 예산을 입력하세요 (USD):",
            default_text=str(get_monthly_budget()),
            ok="저장",
            cancel="취소",
            dimensions=(200, 24),
        ).run()
        if response.clicked:
            try:
                new_budget = float(response.text.strip())
                if new_budget > 0:
                    set_monthly_budget(new_budget)
                    self._refresh_data(None)
                    rumps.notification(
                        APP_NAME,
                        "예산 변경 완료",
                        f"월 예산이 ${new_budget:.2f}로 변경되었습니다.",
                    )
                else:
                    rumps.alert("오류", "예산은 0보다 커야 합니다.")
            except ValueError:
                rumps.alert("오류", "올바른 숫자를 입력해주세요.")


def main():
    # DB가 없으면 자동 초기화
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"
        if schema_path.exists():
            conn = sqlite3.connect(str(DB_PATH))
            with open(schema_path) as f:
                conn.executescript(f.read())
            conn.close()
        else:
            # 최소 스키마 직접 생성
            conn = sqlite3.connect(str(DB_PATH))
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    session_id TEXT DEFAULT '',
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO settings (key, value) VALUES
                    ('monthly_budget_usd', '100.00'),
                    ('alert_threshold_percent', '80'),
                    ('currency', 'USD'),
                    ('theme', 'auto');
                CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
                CREATE INDEX IF NOT EXISTS idx_prompts_provider ON prompts(provider);
            """)
            conn.close()

    app = ClaudeUsageMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
