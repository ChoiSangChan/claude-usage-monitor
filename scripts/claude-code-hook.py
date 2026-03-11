#!/usr/bin/env python3
"""
Claude Code Stop Hook - 세션 종료 시 토큰 사용량을 자동 기록합니다.

Claude Code의 Stop 이벤트에서 transcript_path를 읽어
각 assistant 메시지의 usage 데이터를 파싱하고 SQLite에 저장합니다.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_DIR = Path.home() / ".claude-usage-monitor"
DB_PATH = DB_DIR / "usage.db"
SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "schema.sql"

# 마지막으로 처리한 라인 번호를 저장하는 파일
OFFSET_DIR = DB_DIR / "offsets"

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


def init_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()


def get_db():
    if not DB_PATH.exists():
        init_db()
    return sqlite3.connect(str(DB_PATH))


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model)
    if not pricing:
        for known_model, p in PRICING.items():
            if model.startswith(known_model.rsplit("-", 1)[0]):
                pricing = p
                break
    if not pricing:
        pricing = {"input": 3.00, "output": 15.00}  # 기본값: sonnet급

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def get_offset(transcript_path: str) -> int:
    """이전에 처리한 라인 수를 반환."""
    OFFSET_DIR.mkdir(parents=True, exist_ok=True)
    offset_file = OFFSET_DIR / (Path(transcript_path).stem + ".offset")
    if offset_file.exists():
        return int(offset_file.read_text().strip())
    return 0


def save_offset(transcript_path: str, offset: int):
    """처리한 라인 수를 저장."""
    OFFSET_DIR.mkdir(parents=True, exist_ok=True)
    offset_file = OFFSET_DIR / (Path(transcript_path).stem + ".offset")
    offset_file.write_text(str(offset))


def process_transcript(transcript_path: str, session_id: str):
    """Transcript JSONL 파일에서 새로운 usage 데이터를 추출하고 DB에 기록."""
    path = Path(transcript_path)
    if not path.exists():
        return

    prev_offset = get_offset(transcript_path)

    with open(path) as f:
        lines = f.readlines()

    total_input = 0
    total_output = 0
    model_name = "unknown"
    new_entries = 0

    for i, line in enumerate(lines):
        if i < prev_offset:
            continue

        try:
            data = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        msg = data.get("message", {})
        usage = msg.get("usage")
        if not usage or msg.get("role") != "assistant":
            continue

        model = msg.get("model", "unknown")
        if model != "unknown":
            model_name = model

        input_t = usage.get("input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        output_t = usage.get("output_tokens", 0)

        # 총 입력 토큰 = input + cache_creation + cache_read
        effective_input = input_t + cache_create + cache_read
        total_input += effective_input
        total_output += output_t
        new_entries += 1

    if new_entries == 0:
        save_offset(transcript_path, len(lines))
        return

    cost = calculate_cost(model_name, total_input, total_output)

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO prompts (provider, model, input_tokens, output_tokens, cost_usd, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("anthropic", model_name, total_input, total_output, cost, session_id),
        )
        conn.commit()
    finally:
        conn.close()

    save_offset(transcript_path, len(lines))

    print(
        f"[claude-usage-monitor] {model_name} | "
        f"in: {total_input:,} | out: {total_output:,} | "
        f"cost: ${cost:.4f}",
        file=sys.stderr,
    )


def main():
    init_db()

    # Claude Code hook은 stdin으로 JSON을 전달
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    transcript_path = hook_input.get("transcript_path", "")
    session_id = hook_input.get("session_id", "")

    if not transcript_path:
        return

    process_transcript(transcript_path, session_id)


if __name__ == "__main__":
    main()
