#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v3.0</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>ChoiSangChan</xbar.author.github>
# <xbar.desc>Claude Code 사용량을 JSONL transcript에서 직접 읽어 메뉴바에 표시합니다.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# 10분마다 갱신 (파일명의 .10m.)

import json
import os
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude" / "projects"
CONFIG_PATH = Path.home() / ".claude-usage-monitor" / "config.json"

# Anthropic 가격표 (USD per 1M tokens)
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


def get_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"monthly_budget_usd": 100.0}


def get_pricing(model):
    pricing = PRICING.get(model)
    if not pricing:
        for known_model, p in PRICING.items():
            if model.startswith(known_model.rsplit("-", 1)[0]):
                pricing = p
                break
    return pricing or {"input": 3.00, "output": 15.00}


def scan_jsonl_files():
    """~/.claude/projects/ 아래의 모든 JSONL 파일에서 이번 달 사용량을 집계."""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 모델별 집계: {model: {input_tokens, output_tokens, cost, calls}}
    models = {}
    today_cost = 0.0
    total_cost = 0.0

    if not CLAUDE_DIR.exists():
        return total_cost, today_cost, []

    # 이번 달에 수정된 JSONL 파일만 스캔 (성능 최적화)
    month_start_ts = month_start.timestamp()

    for jsonl_path in CLAUDE_DIR.rglob("*.jsonl"):
        # 파일 수정 시간이 이번 달 이전이면 스킵
        try:
            if jsonl_path.stat().st_mtime < month_start_ts:
                continue
        except OSError:
            continue

        try:
            with open(jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or '"usage"' not in line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = data.get("message", {})
                    if msg.get("role") != "assistant":
                        continue

                    usage = msg.get("usage")
                    if not usage:
                        continue

                    # 타임스탬프 확인 (이번 달 데이터만)
                    ts_str = data.get("timestamp", "")
                    if not ts_str:
                        continue

                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        ts_local = ts.replace(tzinfo=None)  # 로컬 시간으로 비교
                    except (ValueError, AttributeError):
                        continue

                    if ts_local < month_start:
                        continue

                    model = msg.get("model", "unknown")
                    input_t = usage.get("input_tokens", 0)
                    cache_create = usage.get("cache_creation_input_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    output_t = usage.get("output_tokens", 0)

                    effective_input = input_t + cache_create + cache_read

                    pricing = get_pricing(model)
                    cost = (effective_input / 1_000_000) * pricing["input"] + \
                           (output_t / 1_000_000) * pricing["output"]

                    # 모델별 집계
                    if model not in models:
                        models[model] = {"input": 0, "output": 0, "cost": 0.0, "calls": 0}
                    models[model]["input"] += effective_input
                    models[model]["output"] += output_t
                    models[model]["cost"] += cost
                    models[model]["calls"] += 1

                    total_cost += cost

                    if ts_local >= today_start:
                        today_cost += cost

        except (OSError, UnicodeDecodeError):
            continue

    # 모델별 상세 리스트 (비용 내림차순)
    model_details = [
        (model, d["input"], d["output"], d["cost"], d["calls"])
        for model, d in sorted(models.items(), key=lambda x: x[1]["cost"], reverse=True)
    ]

    return total_cost, today_cost, model_details


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
    config = get_config()
    budget = config.get("monthly_budget_usd", 100.0)

    monthly_cost, today_cost, model_details = scan_jsonl_files()
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
        print("📭 사용 기록 없음")
        print("-- ~/.claude/projects/ 에 JSONL 파일이 없습니다 | size=11")

    print("---")
    print("⚙️ 설정")
    print(f"--데이터 소스: ~/.claude/projects/ | size=11 color=#888888")
    print(f"--월 예산: ${budget:.2f} | size=11")
    print(f"--설정 파일: {CONFIG_PATH} | size=11 color=#888888")
    print("---")
    print("🔄 새로고침 | refresh=true")


if __name__ == "__main__":
    main()
