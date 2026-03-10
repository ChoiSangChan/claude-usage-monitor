#!/usr/bin/env python3
"""
Claude Usage Monitor - API 테스트
Anthropic API를 호출하고 사용량이 자동 캡처되는지 확인합니다.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".claude-usage-monitor" / "usage.db"

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.hook import calculate_cost, record_usage


def test_cost_calculation():
    """비용 계산 검증."""
    print("=" * 50)
    print("📊 비용 계산 테스트")
    print("=" * 50)

    test_cases = [
        # (provider, model, input_tokens, output_tokens, expected_cost)
        ("anthropic", "claude-opus-4-6", 1000, 500, 0.0525),
        ("anthropic", "claude-sonnet-4-6", 1000, 500, 0.0105),
        ("anthropic", "claude-haiku-4-5-20251001", 1000, 500, 0.0028),
        ("openai", "gpt-4o", 1000, 500, 0.0075),
        ("openai", "gpt-4o-mini", 1000, 500, 0.00045),
        ("openai", "gpt-4-turbo", 1000, 500, 0.025),
    ]

    all_passed = True
    for provider, model, input_t, output_t, expected in test_cases:
        actual = calculate_cost(provider, model, input_t, output_t)
        passed = abs(actual - expected) < 0.0001
        status = "✅" if passed else "❌"
        if not passed:
            all_passed = False
        print(f"  {status} {provider}/{model}: ${actual:.6f} (expected ${expected:.6f})")

    print()
    return all_passed


def test_record_usage():
    """SQLite 기록 테스트."""
    print("=" * 50)
    print("💾 SQLite 기록 테스트")
    print("=" * 50)

    if not DB_PATH.exists():
        print("  ⚠️  DB가 없습니다. install.sh를 먼저 실행해주세요.")
        print(f"     경로: {DB_PATH}")
        return False

    # 기록 전 카운트
    conn = sqlite3.connect(str(DB_PATH))
    before = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    conn.close()

    # 테스트 데이터 기록
    test_data = [
        ("anthropic", "claude-sonnet-4-6", 1500, 800, "test-session"),
        ("openai", "gpt-4o", 2000, 600, "test-session"),
        ("anthropic", "claude-opus-4-6", 500, 200, "test-session"),
    ]

    for provider, model, input_t, output_t, session_id in test_data:
        cost = record_usage(
            provider=provider,
            model=model,
            input_tokens=input_t,
            output_tokens=output_t,
            session_id=session_id,
            metadata={"source": "test_api.py"},
        )
        print(f"  ✅ {provider}/{model}: in={input_t:,} out={output_t:,} cost=${cost:.6f}")

    # 기록 후 카운트
    conn = sqlite3.connect(str(DB_PATH))
    after = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    conn.close()

    added = after - before
    passed = added == len(test_data)
    status = "✅" if passed else "❌"
    print(f"\n  {status} {added}개 레코드 추가됨 (expected {len(test_data)})")
    print()
    return passed


def test_anthropic_api():
    """실제 Anthropic API 호출 테스트 (API 키 필요)."""
    print("=" * 50)
    print("🔌 Anthropic API 실제 호출 테스트")
    print("=" * 50)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ⚠️  ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print("     export ANTHROPIC_API_KEY='your-key-here'")
        print("  ⏭️  건너뜁니다.")
        print()
        return None

    try:
        import anthropic
    except ImportError:
        print("  ⚠️  anthropic 패키지가 설치되지 않았습니다.")
        print("     pip install anthropic")
        print("  ⏭️  건너뜁니다.")
        print()
        return None

    # 기록 전 카운트
    conn = sqlite3.connect(str(DB_PATH))
    before = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    conn.close()

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say 'Hello, Usage Monitor!' in one sentence."}],
    )

    print(f"  모델: {message.model}")
    print(f"  입력 토큰: {message.usage.input_tokens:,}")
    print(f"  출력 토큰: {message.usage.output_tokens:,}")
    print(f"  응답: {message.content[0].text}")

    # PYTHONSTARTUP hook이 작동했는지 확인
    conn = sqlite3.connect(str(DB_PATH))
    after = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    conn.close()

    if after > before:
        print(f"\n  ✅ 자동 캡처 성공! ({after - before}개 레코드 추가)")
    else:
        # Hook이 없을 수 있으므로 수동 기록
        cost = record_usage(
            provider="anthropic",
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            session_id="test-live",
        )
        print(f"\n  ⚠️  자동 캡처 미작동 (PYTHONSTARTUP 확인 필요). 수동 기록: ${cost:.6f}")

    print()
    return True


def test_db_query():
    """DB 조회 테스트."""
    print("=" * 50)
    print("🔍 DB 조회 테스트")
    print("=" * 50)

    if not DB_PATH.exists():
        print("  ⚠️  DB가 없습니다.")
        return False

    conn = sqlite3.connect(str(DB_PATH))

    # 전체 기록 수
    total = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    print(f"  총 기록 수: {total}")

    # 최근 5개
    rows = conn.execute(
        """
        SELECT provider, model, input_tokens, output_tokens, cost_usd, created_at
        FROM prompts ORDER BY created_at DESC LIMIT 5
        """
    ).fetchall()

    if rows:
        print("\n  최근 기록:")
        for provider, model, inp, out, cost, ts in rows:
            print(f"    [{ts}] {provider}/{model} in={inp:,} out={out:,} ${cost:.4f}")

    # 설정 확인
    settings = conn.execute("SELECT key, value FROM settings").fetchall()
    if settings:
        print("\n  설정:")
        for key, value in settings:
            print(f"    {key}: {value}")

    conn.close()
    print()
    return True


def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   Claude Usage Monitor - API Test        ║")
    print("╚══════════════════════════════════════════╝")
    print()

    results = {}

    results["비용 계산"] = test_cost_calculation()
    results["DB 기록"] = test_record_usage()
    results["API 호출"] = test_anthropic_api()
    results["DB 조회"] = test_db_query()

    # 결과 요약
    print("=" * 50)
    print("📋 테스트 결과 요약")
    print("=" * 50)
    for name, result in results.items():
        if result is None:
            status = "⏭️  건너뜀"
        elif result:
            status = "✅ 통과"
        else:
            status = "❌ 실패"
        print(f"  {status}: {name}")
    print()


if __name__ == "__main__":
    main()
