#!/usr/bin/env python3
"""
LLM API Usage Hook
Anthropic, OpenAI API 호출을 자동으로 캡처하여 SQLite에 저장합니다.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# 가격표 (USD per 1M tokens)
PRICING = {
    "anthropic": {
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    },
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
}

DB_DIR = Path.home() / ".claude-usage-monitor"
DB_PATH = DB_DIR / "usage.db"
SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "schema.sql"


def init_db():
    """데이터베이스 초기화. 디렉토리와 테이블이 없으면 생성."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()


def get_db():
    """SQLite 연결 반환."""
    if not DB_PATH.exists():
        init_db()
    return sqlite3.connect(str(DB_PATH))


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """토큰 수와 모델 기반으로 비용 계산 (USD)."""
    provider_pricing = PRICING.get(provider, {})
    model_pricing = provider_pricing.get(model)

    if not model_pricing:
        # 알려지지 않은 모델은 프리픽스 매칭 시도
        for known_model, pricing in provider_pricing.items():
            if model.startswith(known_model.rsplit("-", 1)[0]):
                model_pricing = pricing
                break

    if not model_pricing:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
    return round(input_cost + output_cost, 6)


def record_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    session_id: str = "",
    metadata: dict | None = None,
):
    """API 사용량을 SQLite에 기록."""
    cost = calculate_cost(provider, model, input_tokens, output_tokens)
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO prompts (provider, model, input_tokens, output_tokens, cost_usd, session_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                model,
                input_tokens,
                output_tokens,
                cost,
                session_id,
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return cost


def parse_anthropic_response(response_data: dict) -> dict:
    """Anthropic API 응답에서 사용량 정보 추출."""
    usage = response_data.get("usage", {})
    return {
        "provider": "anthropic",
        "model": response_data.get("model", "unknown"),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def parse_openai_response(response_data: dict) -> dict:
    """OpenAI API 응답에서 사용량 정보 추출."""
    usage = response_data.get("usage", {})
    return {
        "provider": "openai",
        "model": response_data.get("model", "unknown"),
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


def process_hook_event(event: dict):
    """Hook 이벤트를 처리하여 사용량 기록."""
    provider = event.get("provider", "").lower()
    response_data = event.get("response", {})

    if provider == "anthropic":
        usage_info = parse_anthropic_response(response_data)
    elif provider == "openai":
        usage_info = parse_openai_response(response_data)
    else:
        print(f"Unknown provider: {provider}", file=sys.stderr)
        return

    session_id = event.get("session_id", "")
    metadata = event.get("metadata")

    cost = record_usage(
        provider=usage_info["provider"],
        model=usage_info["model"],
        input_tokens=usage_info["input_tokens"],
        output_tokens=usage_info["output_tokens"],
        session_id=session_id,
        metadata=metadata,
    )

    print(
        f"[{usage_info['provider']}] {usage_info['model']} | "
        f"in: {usage_info['input_tokens']:,} | out: {usage_info['output_tokens']:,} | "
        f"cost: ${cost:.4f}"
    )


def main():
    """stdin에서 JSON 이벤트를 읽어 처리."""
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        print(f"Database initialized at: {DB_PATH}")
        print("Hook is ready. Pipe JSON events to stdin to record usage.")
        return

    print("Listening for API usage events on stdin...", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            process_hook_event(event)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing event: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
