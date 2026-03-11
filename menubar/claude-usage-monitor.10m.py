#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v2.0</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>ChoiSangChan</xbar.author.github>
# <xbar.desc>Claude API 사용량을 메뉴바에 표시합니다.</xbar.desc>
# <xbar.dependencies>python3,sqlite3</xbar.dependencies>
#
# 10분마다 갱신 (파일명의 .10m.)

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".claude-usage-monitor" / "usage.db"

# Anthropic 모델 가격표 (USD per 1M tokens)
PRICING = {
    "claude-opus-4-6":              {"input": 15.00,  "output": 75.00},
    "claude-sonnet-4-6":            {"input": 3.00,   "output": 15.00},
    "claude-haiku-4-5-20251001":    {"input": 0.80,   "output": 4.00},
    "claude-3-5-sonnet-20241022":   {"input": 3.00,   "output": 15.00},
    "claude-3-5-haiku-20241022":    {"input": 0.80,   "output": 4.00},
    "claude-3-opus-20240229":       {"input": 15.00,  "output": 75.00},
    "claude-3-sonnet-20240229":     {"input": 3.00,   "output": 15.00},
    "claude-3-haiku-20240307":      {"input": 0.25,   "output": 1.25},
}


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
        SELECT model,
               SUM(input_tokens) as input_tokens,
               SUM(output_tokens) as output_tokens,
               SUM(cost_usd) as cost,
               COUNT(*) as calls
        FROM prompts
        WHERE created_at >= ?
        GROUP BY model
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


def format_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_bar_color(ratio):
    if ratio < 0.5:
        return "#4CAF50"
    elif ratio < 0.8:
        return "#FF9800"
    else:
        return "#F44336"


def main():
    monthly_cost, model_details = get_monthly_usage()
    today_cost = get_today_usage()
    budget = get_monthly_budget()
    ratio = monthly_cost / budget if budget > 0 else 0
    color = get_bar_color(ratio)

    # 메뉴바 타이틀
    print(f"💬 ${monthly_cost:.2f}/${budget:.0f} | color={color}")
    print("---")

    # 요약
    now = datetime.now()
    print(f"📊 {now.strftime('%Y년 %m월')} Claude 사용량 | size=14")
    print(f"이번 달: ${monthly_cost:.2f} / ${budget:.2f} ({ratio * 100:.1f}%) | color={color}")
    print(f"오늘: ${today_cost:.2f}")
    print("---")

    # 프로그레스 바
    bar_length = 20
    filled = int(bar_length * min(ratio, 1.0))
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"[{bar}] {ratio * 100:.1f}% | font=Menlo size=12")
    print("---")

    # 모델별 상세
    if model_details:
        print("🤖 모델별 사용량 | size=14")
        for model, input_t, output_t, cost, calls in model_details:
            print(f"-- {model} | size=11 font=Menlo")
            print(f"-- 호출: {calls}회 | In: {format_tokens(input_t)} | Out: {format_tokens(output_t)} | size=11")
            print(f"-- 💰 ${cost:.4f} | size=11 color={get_bar_color(cost / budget if budget > 0 else 0)}")
    else:
        print("📭 사용 기록 없음 - Claude Code hook이 설정되었는지 확인하세요")

    print("---")
    print("⚙️ 설정")
    print(f"--DB 경로: {DB_PATH} | size=11 color=#888888")
    print(f"--월 예산: ${budget:.2f} | size=11")
    print("--DB 폴더 열기 | bash=open param1={} terminal=false".format(str(DB_PATH.parent)))
    print("---")
    print("🔄 새로고침 | refresh=true")


if __name__ == "__main__":
    main()
