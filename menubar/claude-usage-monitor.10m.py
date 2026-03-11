#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v4.0</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>ChoiSangChan</xbar.author.github>
# <xbar.desc>Claude Code 사용량 + Anthropic API 빌링 데이터를 메뉴바에 표시합니다.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# 10분마다 갱신 (파일명의 .10m.)

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude" / "projects"
CONFIG_PATH = Path.home() / ".claude-usage-monitor" / "config.json"
CACHE_PATH = Path.home() / ".claude-usage-monitor" / "api_cache.json"

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
    return {"monthly_budget_usd": 200.0}


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_pricing(model):
    pricing = PRICING.get(model)
    if not pricing:
        for known_model, p in PRICING.items():
            if model.startswith(known_model.rsplit("-", 1)[0]):
                pricing = p
                break
    return pricing or {"input": 3.00, "output": 15.00}


# ─────────────────────────────────────────────
# Anthropic Admin API (실제 빌링 데이터)
# ─────────────────────────────────────────────

def fetch_api_cost_report(admin_api_key):
    """Anthropic Admin API에서 이번 달 실제 비용을 조회."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ending = now + timedelta(days=1)

    url = (
        f"https://api.anthropic.com/v1/organizations/cost_report?"
        f"starting_at={month_start.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"ending_at={ending.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"bucket_width=1d&"
        f"group_by[]=description"
    )

    req = urllib.request.Request(url, headers={
        "anthropic-version": "2023-06-01",
        "x-api-key": admin_api_key,
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None


def fetch_api_usage_report(admin_api_key):
    """Anthropic Admin API에서 이번 달 토큰 사용량을 조회."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ending = now + timedelta(days=1)

    url = (
        f"https://api.anthropic.com/v1/organizations/usage_report/messages?"
        f"starting_at={month_start.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"ending_at={ending.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"bucket_width=1d&"
        f"group_by[]=model"
    )

    req = urllib.request.Request(url, headers={
        "anthropic-version": "2023-06-01",
        "x-api-key": admin_api_key,
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None


def get_api_billing_data(config):
    """Admin API로 빌링 데이터를 가져오고 캐시."""
    admin_key = config.get("admin_api_key", "")
    if not admin_key:
        return None

    # 캐시 확인 (5분 이내면 재사용)
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                cache = json.load(f)
            cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
            if (datetime.now() - cached_at).total_seconds() < 300:
                return cache.get("data")
        except Exception:
            pass

    # Cost Report 조회
    cost_data = fetch_api_cost_report(admin_key)
    if not cost_data:
        return None

    # 총 비용 계산 (cents → dollars)
    total_cost_cents = 0
    model_costs = {}
    for bucket in cost_data.get("data", []):
        for item in bucket.get("costs", []):
            amount = float(item.get("amount", "0"))
            total_cost_cents += amount
            desc = item.get("description", "Unknown")
            parsed = item.get("parsed_description", {})
            model_name = parsed.get("model", desc)
            if model_name not in model_costs:
                model_costs[model_name] = 0.0
            model_costs[model_name] += amount

    total_cost_usd = total_cost_cents / 100.0
    model_costs_usd = {k: v / 100.0 for k, v in model_costs.items()}

    result = {
        "total_cost_usd": total_cost_usd,
        "model_costs_usd": model_costs_usd,
        "monthly_limit_usd": config.get("api_monthly_limit_usd", 200.0),
        "credit_balance_usd": config.get("credit_balance_usd"),
    }

    # 캐시 저장
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": result}, f)
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────
# JSONL 스캔 (Claude Code 로컬 사용량)
# ─────────────────────────────────────────────

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

                    # 캐시 토큰은 별도 가격 적용
                    # cache_write: 1.25x input price, cache_read: 0.1x input price
                    pricing = get_pricing(model)
                    cost = (input_t / 1_000_000) * pricing["input"] + \
                           (cache_create / 1_000_000) * pricing["input"] * 1.25 + \
                           (cache_read / 1_000_000) * pricing["input"] * 0.1 + \
                           (output_t / 1_000_000) * pricing["output"]

                    effective_input = input_t + cache_create + cache_read

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


def make_progress_bar(ratio, length=20):
    filled = int(length * min(ratio, 1.0))
    return "█" * filled + "░" * (length - filled)


def main():
    config = get_config()
    budget = config.get("monthly_budget_usd", 200.0)

    # API 빌링 데이터 (Admin API)
    api_data = get_api_billing_data(config)

    # JSONL 로컬 스캔 (Claude Code)
    local_cost, today_cost, model_details = scan_jsonl_files()

    # 메뉴바 타이틀: API 데이터가 있으면 실제 값 사용, 없으면 로컬 추정치
    if api_data:
        display_cost = api_data["total_cost_usd"]
        display_budget = api_data["monthly_limit_usd"]
    else:
        display_cost = local_cost
        display_budget = budget

    ratio = display_cost / display_budget if display_budget > 0 else 0
    color = get_bar_color(ratio)

    # 메뉴바 타이틀
    print(f"💬 ${display_cost:.2f}/${display_budget:.0f} | color={color}")
    print("---")

    now = datetime.now()

    # ─── API 빌링 섹션 (실제 데이터) ───
    if api_data:
        api_cost = api_data["total_cost_usd"]
        api_limit = api_data["monthly_limit_usd"]
        api_ratio = api_cost / api_limit if api_limit > 0 else 0
        api_color = get_bar_color(api_ratio)
        next_reset = now.replace(month=now.month % 12 + 1, day=1) if now.month < 12 else now.replace(year=now.year + 1, month=1, day=1)
        reset_str = next_reset.strftime("%b %-d")

        print(f"📊 API 사용량 (실제 빌링) | size=14")
        print(f"  Monthly limit | size=12 color=#888888")
        bar = make_progress_bar(api_ratio)
        print(f"  [{bar}] | font=Menlo size=11 color={api_color}")
        print(f"  ${api_cost:.2f} of ${api_limit:.2f} ({api_ratio * 100:.0f}% 사용) | color={api_color}")
        print(f"  Resets on {reset_str} | size=11 color=#888888")

        # 크레딧 잔액
        credit = api_data.get("credit_balance_usd")
        if credit is not None:
            print(f"  ---")
            print(f"  Credit balance | size=12 color=#888888")
            print(f"  US${credit:.2f} 잔액 | size=12")

        # API 모델별 비용
        model_costs = api_data.get("model_costs_usd", {})
        if model_costs:
            print(f"  ---")
            print(f"  모델별 비용 | size=12 color=#888888")
            for model_name, cost_usd in sorted(model_costs.items(), key=lambda x: -x[1]):
                if cost_usd > 0.01:
                    print(f"  -- {model_name}: ${cost_usd:.2f} | size=11 font=Menlo")

        print("---")

    # ─── Claude Code 로컬 추정치 섹션 ───
    print(f"💻 Claude Code 추정치 (JSONL) | size=14")
    local_ratio = local_cost / budget if budget > 0 else 0
    local_color = get_bar_color(local_ratio)
    print(f"  이번 달: ${local_cost:.2f} / ${budget:.2f} ({local_ratio * 100:.1f}%) | color={local_color}")
    print(f"  오늘: ${today_cost:.2f}")

    bar = make_progress_bar(local_ratio)
    print(f"  [{bar}] {local_ratio * 100:.1f}% | font=Menlo size=11")

    # 모델별 상세
    if model_details:
        print(f"  ---")
        print(f"  🤖 모델별 사용량 | size=12")
        for model, input_t, output_t, cost, calls in model_details:
            print(f"  -- {model} | size=11 font=Menlo")
            print(f"  -- 호출 {calls}회 · In {format_tokens(input_t)} · Out {format_tokens(output_t)} | size=11")
            print(f"  -- 💰 ${cost:.4f} | size=11 color={get_bar_color(cost / budget if budget > 0 else 0)}")
    else:
        print(f"  📭 사용 기록 없음 | size=11")

    print("---")

    # ─── 캐시 가격 보정 안내 ───
    print(f"ℹ️ 캐시 토큰 가격 보정 적용됨 | size=11 color=#888888")
    print(f"-- cache_write: 1.25x input price | size=10 color=#888888")
    print(f"-- cache_read: 0.1x input price | size=10 color=#888888")

    print("---")

    # ─── 설정 ───
    print("⚙️ 설정")
    if config.get("admin_api_key"):
        print(f"--✅ Admin API 연결됨 | size=11 color=#4CAF50")
    else:
        print(f"--⚠️ Admin API 미설정 | size=11 color=#FF9800")
        print(f"--  config.json에 admin_api_key 추가 필요 | size=10 color=#888888")
    print(f"--데이터 소스: ~/.claude/projects/ | size=11 color=#888888")
    print(f"--월 예산 (로컬): ${budget:.2f} | size=11")
    print(f"--설정 파일: {CONFIG_PATH} | size=11 color=#888888")
    print("---")

    # 마지막 업데이트
    update_time = now.strftime("%H:%M")
    print(f"🔄 새로고침 (마지막: {update_time}) | refresh=true")


if __name__ == "__main__":
    main()
