#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v5.0</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>ChoiSangChan</xbar.author.github>
# <xbar.desc>Anthropic API 실제 빌링 + Claude Code JSONL 추정치를 메뉴바에 표시합니다.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# 10분마다 갱신 (파일명의 .10m.)
#
# 자동 조회 데이터:
#   1) API Monthly Limit  — Admin API /v1/organizations/cost_report
#   2) Credit Balance      — Admin API 잔액 조회
#   3) Claude Code 추정치  — 로컬 JSONL 파싱 (캐시 토큰 가격 보정 적용)

import json
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
    return {}


def get_pricing(model):
    pricing = PRICING.get(model)
    if not pricing:
        for known_model, p in PRICING.items():
            if model.startswith(known_model.rsplit("-", 1)[0]):
                pricing = p
                break
    return pricing or {"input": 3.00, "output": 15.00}


def get_bar_color(ratio):
    if ratio < 0.5:
        return "#4CAF50"
    elif ratio < 0.8:
        return "#FF9800"
    else:
        return "#F44336"


def make_bar(ratio, length=20):
    filled = int(length * min(ratio, 1.0))
    return "█" * filled + "░" * (length - filled)


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def next_month_first():
    now = datetime.now()
    if now.month < 12:
        return now.replace(month=now.month + 1, day=1)
    return now.replace(year=now.year + 1, month=1, day=1)


# ═══════════════════════════════════════════════════
# 1) API Monthly Limit — Anthropic Admin API 자동 조회
# ═══════════════════════════════════════════════════

def fetch_admin_api(admin_key):
    """Admin API cost_report 조회 (5분 캐시)."""
    # 캐시 확인
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                cache = json.load(f)
            cached_at = datetime.fromisoformat(cache["cached_at"])
            if (datetime.now() - cached_at).total_seconds() < 300:
                return cache["data"]
        except Exception:
            pass

    now = datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now + timedelta(days=1)

    url = (
        f"https://api.anthropic.com/v1/organizations/cost_report?"
        f"starting_at={start.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"ending_at={end.strftime('%Y-%m-%dT00:00:00Z')}&"
        f"bucket_width=1d&"
        f"group_by[]=description"
    )
    req = urllib.request.Request(url, headers={
        "anthropic-version": "2023-06-01",
        "x-api-key": admin_key,
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except Exception:
        return None

    # 파싱
    total_cents = 0
    by_model = {}
    for bucket in raw.get("data", []):
        for item in bucket.get("costs", []):
            amt = float(item.get("amount", "0"))
            total_cents += amt
            parsed = item.get("parsed_description", {})
            name = parsed.get("model", item.get("description", "unknown"))
            by_model[name] = by_model.get(name, 0) + amt

    result = {
        "cost_usd": total_cents / 100.0,
        "models": {k: v / 100.0 for k, v in by_model.items()},
    }

    # 캐시 저장
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": result}, f)
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════
# 2) Claude Code JSONL 로컬 스캔 — 자동 조회
# ═══════════════════════════════════════════════════

def scan_jsonl():
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_ts = month_start.timestamp()

    models = {}
    today_cost = 0.0
    total_cost = 0.0

    if not CLAUDE_DIR.exists():
        return total_cost, today_cost, []

    for path in CLAUDE_DIR.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < month_ts:
                continue
        except OSError:
            continue

        try:
            with open(path) as f:
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

                    ts_str = data.get("timestamp", "")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        ts_local = ts.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        continue
                    if ts_local < month_start:
                        continue

                    model = msg.get("model", "unknown")
                    inp = usage.get("input_tokens", 0)
                    cw = usage.get("cache_creation_input_tokens", 0)
                    cr = usage.get("cache_read_input_tokens", 0)
                    out = usage.get("output_tokens", 0)

                    p = get_pricing(model)
                    cost = (inp / 1e6) * p["input"] + \
                           (cw / 1e6) * p["input"] * 1.25 + \
                           (cr / 1e6) * p["input"] * 0.1 + \
                           (out / 1e6) * p["output"]

                    eff_in = inp + cw + cr
                    if model not in models:
                        models[model] = {"in": 0, "out": 0, "cost": 0.0, "calls": 0}
                    models[model]["in"] += eff_in
                    models[model]["out"] += out
                    models[model]["cost"] += cost
                    models[model]["calls"] += 1

                    total_cost += cost
                    if ts_local >= today_start:
                        today_cost += cost

        except (OSError, UnicodeDecodeError):
            continue

    details = [
        (m, d["in"], d["out"], d["cost"], d["calls"])
        for m, d in sorted(models.items(), key=lambda x: x[1]["cost"], reverse=True)
    ]
    return total_cost, today_cost, details


# ═══════════════════════════════════════════════════
# 메뉴바 출력
# ═══════════════════════════════════════════════════

def main():
    config = get_config()
    budget = config.get("monthly_budget_usd", 200.0)
    api_limit = config.get("api_monthly_limit_usd", 200.0)

    # ── 데이터 자동 조회 ──
    admin_key = config.get("admin_api_key", "")
    api_data = fetch_admin_api(admin_key) if admin_key else None
    local_cost, today_cost, model_details = scan_jsonl()

    # ── 메뉴바 타이틀 ──
    if api_data:
        title_cost = api_data["cost_usd"]
        title_limit = api_limit
    else:
        title_cost = local_cost
        title_limit = budget

    ratio = title_cost / title_limit if title_limit > 0 else 0
    color = get_bar_color(ratio)
    print(f"💬 ${title_cost:.2f}/${title_limit:.0f} | color={color}")
    print("---")

    now = datetime.now()
    reset_date = next_month_first().strftime("%-d %b %Y")

    # ╔═══════════════════════════════════════════╗
    # ║  섹션 1: API Monthly Limit (실제 청구액)  ║
    # ╚═══════════════════════════════════════════╝
    print("💰 API Monthly Limit (실제 청구액) | size=14")
    if api_data:
        api_cost = api_data["cost_usd"]
        api_ratio = api_cost / api_limit if api_limit > 0 else 0
        api_color = get_bar_color(api_ratio)
        bar = make_bar(api_ratio)

        print(f"  [{bar}] | font=Menlo size=11 color={api_color}")
        print(f"  ${api_cost:.2f} of ${api_limit:.2f} | size=13")
        print(f"  Resets on {reset_date} | size=11 color=#888888")
        print(f"  ---")

        # 모델별 청구 비용
        for name, usd in sorted(api_data["models"].items(), key=lambda x: -x[1]):
            if usd >= 0.01:
                pct = (usd / api_cost * 100) if api_cost > 0 else 0
                print(f"  {name}: ${usd:.2f} ({pct:.0f}%) | size=11 font=Menlo")

        print(f"  ---")
        print(f"  소스: Anthropic Admin API (자동) | size=10 color=#4CAF50")
    else:
        print(f"  ⚠️ admin_api_key 미설정 | size=11 color=#FF9800")
        print(f"  config.json에 admin_api_key 추가 시 자동 조회 | size=10 color=#888888")

    print("---")

    # ╔═══════════════════════════════════════════╗
    # ║  섹션 2: Credit Balance (크레딧 잔액)     ║
    # ╚═══════════════════════════════════════════╝
    print("💳 Credit Balance (API 크레딧 잔액) | size=14")
    if api_data:
        # pending = 이번 달 실제 청구액
        pending = api_data["cost_usd"]
        # remaining은 config에서 가져옴 (API에 별도 엔드포인트 없음)
        remaining = config.get("credit_balance_usd")
        if remaining is not None:
            print(f"  US${remaining:.2f} | size=16")
            print(f"  Remaining Balance | size=11 color=#888888")
            print(f"  US${pending:.2f} pending this period | size=11 color=#FF9800")
            print(f"  ---")
            print(f"  잔액: config.json (수동) | 청구액: Admin API (자동) | size=10 color=#888888")
        else:
            print(f"  US${pending:.2f} pending this period | size=11 color=#FF9800")
            print(f"  ---")
            print(f"  잔액 표시: config.json에 credit_balance_usd 추가 | size=10 color=#888888")
    else:
        remaining = config.get("credit_balance_usd")
        if remaining is not None:
            print(f"  US${remaining:.2f} | size=16")
            print(f"  Remaining Balance (config 수동 입력) | size=11 color=#888888")
        else:
            print(f"  ⚠️ 데이터 없음 | size=11 color=#FF9800")

    print("---")

    # ╔═══════════════════════════════════════════╗
    # ║  섹션 3: Claude Code 사용량 (JSONL 추정)  ║
    # ╚═══════════════════════════════════════════╝
    print("💻 Claude Code 사용량 (JSONL 추정치) | size=14")
    local_ratio = local_cost / budget if budget > 0 else 0
    local_color = get_bar_color(local_ratio)
    bar = make_bar(local_ratio)

    print(f"  이번 달 추정: ${local_cost:.2f} / ${budget:.2f} ({local_ratio * 100:.1f}%) | color={local_color}")
    print(f"  오늘 추정:    ${today_cost:.2f} | size=12")
    print(f"  [{bar}] {local_ratio * 100:.1f}% | font=Menlo size=11 color={local_color}")

    if model_details:
        print(f"  ---")
        for model, in_t, out_t, cost, calls in model_details:
            pct = (cost / local_cost * 100) if local_cost > 0 else 0
            print(f"  {model} | size=11 font=Menlo")
            print(f"  -- ${cost:.4f} ({pct:.0f}%) · {calls}회 · In {fmt_tokens(in_t)} · Out {fmt_tokens(out_t)} | size=10")
    else:
        print(f"  📭 이번 달 사용 기록 없음 | size=11")

    print(f"  ---")
    print(f"  소스: ~/.claude/projects/ JSONL (자동) | size=10 color=#4CAF50")
    print(f"  캐시 가격: write 1.25x, read 0.1x 적용 | size=10 color=#888888")

    print("---")

    # ╔═══════════════════════════════════════════╗
    # ║  설정 상태                                ║
    # ╚═══════════════════════════════════════════╝
    print("⚙️ 데이터 소스 상태")
    print(f"--API Monthly Limit: {'✅ Admin API 자동' if admin_key else '❌ 미연결'} | size=11 color={'#4CAF50' if admin_key else '#F44336'}")
    print(f"--Credit Balance: {'📝 config 수동' if config.get('credit_balance_usd') is not None else '❌ 미설정'} | size=11 color={'#FF9800' if config.get('credit_balance_usd') is not None else '#F44336'}")
    print(f"--Claude Code JSONL: ✅ 자동 스캔 | size=11 color=#4CAF50")
    print(f"--설정: {CONFIG_PATH} | size=10 color=#888888")
    print("---")

    update_time = now.strftime("%H:%M")
    print(f"🔄 새로고침 (마지막: {update_time}) | refresh=true")


if __name__ == "__main__":
    main()
