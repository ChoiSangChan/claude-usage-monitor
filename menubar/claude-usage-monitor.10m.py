#!/usr/bin/env python3
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v5.1</xbar.version>
# <xbar.author>claude-usage-monitor</xbar.author>
# <xbar.author.github>ChoiSangChan</xbar.author.github>
# <xbar.desc>Anthropic API 실제 청구액 + Claude Code API 사용 추정치를 메뉴바에 표시합니다.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# 10분마다 갱신 (파일명의 .10m.)
#
# 자동 조회 데이터:
#   1) API Monthly Limit  — Anthropic Admin API 실제 청구액
#   2) Claude Code API 사용 추정 — 로컬 JSONL 기반 API 비용 추정

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude" / "projects"
CONFIG_PATH = Path.home() / ".claude-usage-monitor" / "config.json"
CACHE_PATH = Path.home() / ".claude-usage-monitor" / "api_cache.json"

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


def color_for(ratio):
    if ratio < 0.5:
        return "#4CAF50"
    elif ratio < 0.8:
        return "#FF9800"
    return "#F44336"


def bar(ratio, length=20):
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
# Admin API — Anthropic 실제 청구액 자동 조회
# ═══════════════════════════════════════════════════

def fetch_admin_api(admin_key):
    """Admin API cost_report 조회 (5분 캐시)."""
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

    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": result}, f)
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════
# JSONL 스캔 — Claude Code API 사용량 추정
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
    api_limit = config.get("api_monthly_limit_usd", 200.0)

    # ── 자동 조회 ──
    admin_key = config.get("admin_api_key", "")
    api_data = fetch_admin_api(admin_key) if admin_key else None
    local_cost, today_cost, model_details = scan_jsonl()

    # ── 메뉴바 타이틀 ──
    if api_data:
        title_cost = api_data["cost_usd"]
    else:
        title_cost = local_cost

    ratio = title_cost / api_limit if api_limit > 0 else 0
    print(f"💬 ${title_cost:.2f}/${api_limit:.0f} | color={color_for(ratio)}")
    print("---")

    now = datetime.now()
    reset_date = next_month_first().strftime("%-d %b %Y")

    # ╔═══════════════════════════════════════════════════╗
    # ║  API Monthly Limit — Anthropic 콘솔 실제 청구액   ║
    # ╚═══════════════════════════════════════════════════╝
    print("💰 API Monthly Limit | size=14")
    print("Anthropic Console 실제 청구액 | size=11 color=#888888")
    if api_data:
        api_cost = api_data["cost_usd"]
        api_ratio = api_cost / api_limit if api_limit > 0 else 0
        c = color_for(api_ratio)

        print(f"[{bar(api_ratio)}] | font=Menlo size=11 color={c}")
        print(f"${api_cost:.2f} of ${api_limit:.2f} | size=13 color={c}")
        print(f"Resets on {reset_date} | size=11 color=#888888")
        print(f"---")

        # 모델별 비용
        for name, usd in sorted(api_data["models"].items(), key=lambda x: -x[1]):
            if usd >= 0.01:
                pct = (usd / api_cost * 100) if api_cost > 0 else 0
                print(f"  {name}: ${usd:.2f} ({pct:.0f}%) | size=11 font=Menlo")
    else:
        print("⚠️ admin_api_key 미설정 — config.json에 추가 필요 | size=11 color=#FF9800")

    print("---")

    # ╔═══════════════════════════════════════════════════╗
    # ║  Claude Code API 사용 추정 — JSONL 기반 추정치    ║
    # ╚═══════════════════════════════════════════════════╝
    print("💻 Claude Code API 사용 추정 | size=14")
    print("API Monthly Limit 중 Claude Code 사용분 | size=11 color=#888888")

    local_ratio = local_cost / api_limit if api_limit > 0 else 0
    c = color_for(local_ratio)

    print(f"[{bar(local_ratio)}] | font=Menlo size=11 color={c}")
    print(f"이번 달: ${local_cost:.2f} (한도 ${api_limit:.0f} 중 {local_ratio * 100:.1f}%) | color={c}")
    print(f"오늘:    ${today_cost:.2f} | size=12")

    if api_data:
        # API 실제값과 비교
        diff = api_data["cost_usd"] - local_cost
        if abs(diff) > 0.01:
            print(f"---")
            if diff > 0:
                print(f"API 실제 청구액과 차이: +${diff:.2f} (다른 API 사용분 포함) | size=10 color=#888888")
            else:
                print(f"API 실제 청구액과 차이: -${abs(diff):.2f} (추정 오차) | size=10 color=#888888")

    if model_details:
        print(f"---")
        for model, in_t, out_t, cost, calls in model_details:
            pct = (cost / local_cost * 100) if local_cost > 0 else 0
            print(f"  {model} | size=11 font=Menlo")
            print(f"  -- ${cost:.4f} ({pct:.0f}%) · {calls}회 · In {fmt_tokens(in_t)} Out {fmt_tokens(out_t)} | size=10")
    else:
        print(f"📭 이번 달 사용 기록 없음 | size=11")

    print("---")

    # ╔═══════════════════════════════════════════════════╗
    # ║  설정                                             ║
    # ╚═══════════════════════════════════════════════════╝
    print("⚙️ 설정")
    print(f"--API Monthly Limit: {'✅ 자동 (Admin API)' if admin_key else '❌ 미연결'} | size=11 color={'#4CAF50' if admin_key else '#F44336'}")
    print(f"--Claude Code 추정: ✅ 자동 (JSONL 스캔) | size=11 color=#4CAF50")
    print(f"--캐시 가격 보정: write 1.25x, read 0.1x | size=10 color=#888888")
    print(f"--설정 파일: {CONFIG_PATH} | size=10 color=#888888")
    print("---")

    print(f"🔄 새로고침 (마지막: {now.strftime('%H:%M')}) | refresh=true")


if __name__ == "__main__":
    main()
