#!/usr/bin/env python3
"""
Claude Usage Monitor - Standalone macOS Menu Bar App (v6.0)
rumps 기반 독립 실행형 메뉴바 앱. 10분마다 사용량을 자동 갱신합니다.

자동 조회 데이터:
  1) API Monthly Limit  — Anthropic Admin API 실제 청구액
  2) Claude Code API 사용 추정 — 로컬 JSONL 기반 API 비용 추정
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

try:
    import rumps
except ImportError:
    rumps = None

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
APP_NAME = "Claude Usage Monitor"
REFRESH_INTERVAL_SEC = 600  # 10분 (초)
CLAUDE_DIR = Path.home() / ".claude" / "projects"
CONFIG_PATH = Path.home() / ".claude-usage-monitor" / "config.json"
API_CACHE_PATH = Path.home() / ".claude-usage-monitor" / "api_cache.json"

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


# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
def get_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


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


def format_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ─────────────────────────────────────────────
# Admin API — Anthropic 실제 청구액 자동 조회
# ─────────────────────────────────────────────
def fetch_admin_api(admin_key):
    """Admin API cost_report 조회 (5분 캐시)."""
    if API_CACHE_PATH.exists():
        try:
            with open(API_CACHE_PATH) as f:
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
        API_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(API_CACHE_PATH, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": result}, f)
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────
# JSONL 스캔 — Claude Code API 사용량 추정
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# macOS Menu Bar App (v6.0)
# ─────────────────────────────────────────────

_MENU_REFRESH = "\U0001F504 새로고침 (10분 자동)"
_LABEL_QUIT = "종료"
_LABEL_SETTINGS = "\u2699\uFE0F 설정"
_LABEL_API_SECTION = "\U0001F4B0 API Monthly Limit"
_LABEL_JSONL_SECTION = "\U0001F4BB Claude Code API 사용 추정"


def _noop_decorator(*args, **kwargs):
    """rumps.timer fallback decorator (no-op) for non-macOS."""
    def wrapper(func):
        return func
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return wrapper


if rumps is not None:
    _base_class = rumps.App
    _timer = rumps.timer
else:
    class _base_class:
        def __init__(self, *args, **kwargs):
            self.title = ""
            self.menu = {}
        def run(self):
            print("rumps is required for the menu bar app (macOS only).")
            print("Install with: pip install rumps")
            sys.exit(1)
    _timer = _noop_decorator


class ClaudeUsageMonitorApp(_base_class):
    def __init__(self):
        if rumps is not None:
            super().__init__(
                APP_NAME,
                title="\U0001F4AC $0.00",
                quit_button=rumps.MenuItem(_LABEL_QUIT, key="q"),
            )
            self._build_menu()
        else:
            super().__init__()
        self._refresh_data(None)

    def _build_menu(self):
        self.menu = [
            # API Monthly Limit 섹션
            rumps.MenuItem("api_header", callback=None),
            rumps.MenuItem("api_subtitle", callback=None),
            rumps.MenuItem("api_cost", callback=None),
            rumps.MenuItem("api_reset", callback=None),
            None,
            rumps.MenuItem("api_models_header", callback=None),
            None,
            # Claude Code JSONL 섹션
            rumps.MenuItem("jsonl_header", callback=None),
            rumps.MenuItem("jsonl_subtitle", callback=None),
            rumps.MenuItem("jsonl_month", callback=None),
            rumps.MenuItem("jsonl_today", callback=None),
            rumps.MenuItem("jsonl_diff", callback=None),
            None,
            rumps.MenuItem("jsonl_models_header", callback=None),
            None,
            # 설정
            rumps.MenuItem("settings_menu"),
            None,
            rumps.MenuItem(_MENU_REFRESH, callback=self._refresh_data, key="r"),
        ]
        self._build_settings_submenu()

    def _build_settings_submenu(self):
        settings_menu = self.menu["settings_menu"]
        settings_menu.title = _LABEL_SETTINGS

        config = get_config()
        admin_key = config.get("admin_api_key", "")

        if admin_key:
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 Admin API Key: \u2705 연결됨", callback=None
            ))
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 API Key 변경하기", callback=self._set_api_key
            ))
        else:
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 Admin API Key: \u274C 미설정", callback=None
            ))
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 API Key 등록하기", callback=self._set_api_key
            ))
        settings_menu.add(None)
        settings_menu.add(rumps.MenuItem(
            "Claude Code 추정: \u2705 자동 (JSONL 스캔)", callback=None
        ))
        settings_menu.add(rumps.MenuItem(
            "캐시 가격 보정: write 1.25x, read 0.1x", callback=None
        ))
        settings_menu.add(None)
        settings_menu.add(rumps.MenuItem(
            f"설정 파일: {CONFIG_PATH}", callback=None
        ))
        settings_menu.add(rumps.MenuItem(
            "\U0001F4C2 설정 폴더 열기", callback=self._open_config_folder
        ))

    # ─────────────────────────────────────────
    # Timer: 10분마다 자동 갱신
    # ─────────────────────────────────────────
    @_timer(REFRESH_INTERVAL_SEC)
    def _auto_refresh(self, _):
        self._refresh_data(None)

    # ─────────────────────────────────────────
    # 데이터 갱신
    # ─────────────────────────────────────────
    def _refresh_data(self, _):
        config = get_config()
        admin_key = config.get("admin_api_key", "")
        api_data = fetch_admin_api(admin_key) if admin_key else None
        local_cost, today_cost, model_details = scan_jsonl()

        # 메뉴바 타이틀 — 사용액만 표시 (한도 없음)
        if api_data:
            title_cost = api_data["cost_usd"]
        else:
            title_cost = local_cost
        self.title = f"\U0001F4AC ${title_cost:.2f}"

        if rumps is None:
            return

        now = datetime.now()

        # ── API Monthly Limit 섹션 ──
        self.menu["api_header"].title = _LABEL_API_SECTION
        self.menu["api_subtitle"].title = "  Anthropic Console 실제 청구액"

        if api_data:
            api_cost = api_data["cost_usd"]
            self.menu["api_cost"].title = f"  이번 달: ${api_cost:.2f}"

            next_month = now.replace(day=1, month=now.month + 1) if now.month < 12 else now.replace(year=now.year + 1, month=1, day=1)
            self.menu["api_reset"].title = f"  Resets on {next_month.strftime('%-d %b %Y')}"

            # 모델별 비용
            self._update_api_models(api_data)
        else:
            self.menu["api_cost"].title = "  \u26A0\uFE0F Admin API Key 미설정"
            self.menu["api_reset"].title = "  설정 → API Key 등록하기"
            self.menu["api_models_header"].title = ""

        # ── Claude Code JSONL 섹션 ──
        self.menu["jsonl_header"].title = _LABEL_JSONL_SECTION
        self.menu["jsonl_subtitle"].title = "  로컬 JSONL 기반 API 비용 추정"
        self.menu["jsonl_month"].title = f"  이번 달: ${local_cost:.2f}"
        self.menu["jsonl_today"].title = f"  오늘: ${today_cost:.2f}"

        # API 실제값과 비교
        if api_data:
            diff = api_data["cost_usd"] - local_cost
            if abs(diff) > 0.01:
                if diff > 0:
                    self.menu["jsonl_diff"].title = f"  API 실제 청구액과 차이: +${diff:.2f} (다른 API 사용분)"
                else:
                    self.menu["jsonl_diff"].title = f"  API 실제 청구액과 차이: -${abs(diff):.2f} (추정 오차)"
            else:
                self.menu["jsonl_diff"].title = ""
        else:
            self.menu["jsonl_diff"].title = ""

        # 모델별 상세
        self._update_jsonl_models(model_details, local_cost)

        # 마지막 갱신 시각
        self.menu[_MENU_REFRESH].title = f"\U0001F504 새로고침 (마지막: {now.strftime('%H:%M:%S')})"

    def _update_api_models(self, api_data):
        header = self.menu["api_models_header"]
        # 기존 동적 항목 제거
        keys_to_remove = [
            k for k in self.menu.keys()
            if isinstance(k, str) and k.startswith("_api_dyn_")
        ]
        for k in keys_to_remove:
            del self.menu[k]

        api_cost = api_data["cost_usd"]
        if not api_data["models"]:
            header.title = ""
            return

        header.title = "  모델별 비용"
        idx = 0
        for name, usd in sorted(api_data["models"].items(), key=lambda x: -x[1]):
            if usd >= 0.01:
                pct = (usd / api_cost * 100) if api_cost > 0 else 0
                key = f"_api_dyn_{idx:03d}"
                item = rumps.MenuItem(f"    {name}: ${usd:.2f} ({pct:.0f}%)")
                self.menu.insert_after("api_models_header", rumps.MenuItem(key))
                self.menu[key] = item
                self.menu[key].title = item.title
                idx += 1

    def _update_jsonl_models(self, model_details, local_cost):
        header = self.menu["jsonl_models_header"]
        keys_to_remove = [
            k for k in self.menu.keys()
            if isinstance(k, str) and k.startswith("_jsonl_dyn_")
        ]
        for k in keys_to_remove:
            del self.menu[k]

        if not model_details:
            header.title = "  \U0001F4ED 이번 달 사용 기록 없음"
            return

        header.title = "  모델별 사용량"
        idx = 0
        for model, in_t, out_t, cost, calls in model_details:
            pct = (cost / local_cost * 100) if local_cost > 0 else 0
            key = f"_jsonl_dyn_{idx:03d}"
            model_item = rumps.MenuItem(f"    {model}")
            detail = rumps.MenuItem(
                f"      ${cost:.4f} ({pct:.0f}%) · {calls}회 · In {format_tokens(in_t)} Out {format_tokens(out_t)}"
            )
            model_item.add(detail)
            self.menu.insert_after("jsonl_models_header", rumps.MenuItem(key))
            self.menu[key] = model_item
            self.menu[key].title = model_item.title
            idx += 1

    # ─────────────────────────────────────────
    # 액션
    # ─────────────────────────────────────────
    def _open_config_folder(self, _):
        os.system(f'open "{CONFIG_PATH.parent}"')

    def _set_api_key(self, _):
        response = rumps.Window(
            title="Admin API Key 설정",
            message="Anthropic Admin API Key를 입력하세요:\n(sk-ant-admin01-...)",
            default_text="",
            ok="저장",
            cancel="취소",
            dimensions=(400, 24),
        ).run()
        if response.clicked:
            key = response.text.strip()
            if key and key.startswith("sk-ant-admin"):
                config = get_config()
                config["admin_api_key"] = key
                save_config(config)
                # 캐시 초기화
                if API_CACHE_PATH.exists():
                    API_CACHE_PATH.unlink()
                rumps.notification(
                    APP_NAME,
                    "API Key 설정 완료",
                    "Admin API Key가 저장되었습니다. 새로고침합니다.",
                )
                self._refresh_data(None)
                # 설정 메뉴 재구성
                self._rebuild_settings()
            elif key:
                rumps.alert("오류", "올바른 Admin API Key 형식이 아닙니다.\n(sk-ant-admin01-...로 시작해야 합니다)")

    def _rebuild_settings(self):
        """설정 메뉴를 재구성."""
        settings_menu = self.menu["settings_menu"]
        settings_menu.clear()
        config = get_config()
        admin_key = config.get("admin_api_key", "")

        if admin_key:
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 Admin API Key: \u2705 연결됨", callback=None
            ))
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 API Key 변경하기", callback=self._set_api_key
            ))
        else:
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 Admin API Key: \u274C 미설정", callback=None
            ))
            settings_menu.add(rumps.MenuItem(
                "\U0001F511 API Key 등록하기", callback=self._set_api_key
            ))
        settings_menu.add(None)
        settings_menu.add(rumps.MenuItem(
            "Claude Code 추정: \u2705 자동 (JSONL 스캔)", callback=None
        ))
        settings_menu.add(rumps.MenuItem(
            "캐시 가격 보정: write 1.25x, read 0.1x", callback=None
        ))
        settings_menu.add(None)
        settings_menu.add(rumps.MenuItem(
            f"설정 파일: {CONFIG_PATH}", callback=None
        ))
        settings_menu.add(rumps.MenuItem(
            "\U0001F4C2 설정 폴더 열기", callback=self._open_config_folder
        ))


def main():
    app = ClaudeUsageMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
