#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>claude-usage-monitor</xbar.author.github>
# <xbar.desc>LLM API 사용량을 메뉴바에 표시합니다.</xbar.desc>
# <xbar.image>https://github.com/claude-usage-monitor</xbar.image>
# <xbar.dependencies>python3,sqlite3</xbar.dependencies>
# <xbar.abouturl>https://github.com/claude-usage-monitor</xbar.abouturl>
#
# 10분마다 갱신 (파일명의 .10m.)

import sqlite3
import os
from datetime import datetime
from pathlib import Path

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


def get_db():
    """SQLite 연결."""
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(str(DB_PATH))


def get_monthly_usage():
    """이번 달 총 사용량 조회."""
    conn = get_db()
    if not conn:
        return 0.0, []

    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")

    # 총 비용
    cursor = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM prompts WHERE created_at >= ?",
        (month_start,),
    )
    total_cost = cursor.fetchone()[0]

    # 모델별 상세
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
    """오늘 사용량 조회."""
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
    """월 예산 조회."""
    conn = get_db()
    if not conn:
        return 200.0

    cursor = conn.execute(
        "SELECT value FROM settings WHERE key = 'monthly_budget_usd'"
    )
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 200.0


def format_tokens(n):
    """토큰 수를 읽기 좋게 포맷."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_bar_color(ratio):
    """예산 사용 비율에 따른 색상."""
    if ratio < 0.5:
        return "#4CAF50"  # 녹색
    elif ratio < 0.8:
        return "#FF9800"  # 주황
    else:
        return "#F44336"  # 빨강


def main():
    monthly_cost, model_details = get_monthly_usage()
    today_cost = get_today_usage()
    budget = get_monthly_budget()
    ratio = monthly_cost / budget if budget > 0 else 0

    color = get_bar_color(ratio)

    # ─────────────────────────────────────────
    # 메뉴바 타이틀 (항상 표시)
    # ─────────────────────────────────────────
    print(f"💬 ${monthly_cost:.0f}/${budget:.0f} | color={color}")
    print("---")

    # ─────────────────────────────────────────
    # 요약 섹션
    # ─────────────────────────────────────────
    now = datetime.now()
    print(f"📊 {now.strftime('%Y년 %m월')} 사용량 | size=14")
    print(f"이번 달: ${monthly_cost:.2f} / ${budget:.2f} ({ratio * 100:.1f}%) | color={color}")
    print(f"오늘: ${today_cost:.2f}")
    print("---")

    # ─────────────────────────────────────────
    # 프로그레스 바
    # ─────────────────────────────────────────
    bar_length = 20
    filled = int(bar_length * min(ratio, 1.0))
    empty = bar_length - filled
    bar = "█" * filled + "░" * empty
    print(f"[{bar}] {ratio * 100:.1f}% | font=Menlo size=12")
    print("---")

    # ─────────────────────────────────────────
    # 모델별 상세 드롭다운
    # ─────────────────────────────────────────
    if model_details:
        print("🤖 모델별 사용량 | size=14")

        # Provider별 그룹핑
        providers = {}
        for provider, model, input_t, output_t, cost, calls in model_details:
            if provider not in providers:
                providers[provider] = []
            providers[provider].append((model, input_t, output_t, cost, calls))

        for provider, models in sorted(providers.items()):
            provider_cost = sum(m[3] for m in models)
            print(f"--📦 {provider.upper()} (${provider_cost:.2f}) | size=13")
            for model, input_t, output_t, cost, calls in models:
                print(f"---- {model} | size=11 font=Menlo")
                print(f"---- 호출: {calls}회 | In: {format_tokens(input_t)} | Out: {format_tokens(output_t)} | size=11")
                print(f"---- 💰 ${cost:.4f} | size=11 color={get_bar_color(cost / budget if budget > 0 else 0)}")
    else:
        print("📭 이번 달 사용 기록이 없습니다.")

    print("---")

    # ─────────────────────────────────────────
    # 가격표
    # ─────────────────────────────────────────
    print("💵 모델 가격표 (per 1M tokens) | size=14")
    current_provider = ""
    for model_name, info in sorted(PRICING.items(), key=lambda x: (x[1]["provider"], x[0])):
        provider = info["provider"]
        if provider != current_provider:
            print(f"--📦 {provider} | size=13")
            current_provider = provider
        print(f"---- {model_name} | size=11 font=Menlo")
        print(f"---- In: ${info['input']:.2f}  Out: ${info['output']:.2f} | size=10 color=#888888")

    print("---")

    # ─────────────────────────────────────────
    # 설정 / 액션
    # ─────────────────────────────────────────
    print("⚙️ 설정")
    print(f"--DB 경로: {DB_PATH} | size=11 color=#888888")
    print(f"--월 예산: ${budget:.2f} | size=11")
    print("--DB 열기 | bash=open param1={} terminal=false".format(str(DB_PATH.parent)))
    print("---")
    print("🔄 새로고침 | refresh=true")


if __name__ == "__main__":
    main()
