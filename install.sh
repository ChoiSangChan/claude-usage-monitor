#!/bin/bash
#
# Claude Usage Monitor - 자동 설치 스크립트
# macOS에서 LLM API 사용량을 자동 추적하도록 설정합니다.
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_DIR="$HOME/.claude-usage-monitor"
DB_PATH="$DB_DIR/usage.db"
XBAR_PLUGIN_DIR="$HOME/Library/Application Support/xbar/plugins"
HOOK_PATH="$INSTALL_DIR/scripts/hook.py"
STARTUP_SCRIPT="$DB_DIR/pythonstartup.py"

print_step() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} ${GREEN}▶${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✖${NC}  $1"
}

print_done() {
    echo -e "${GREEN}✔${NC}  $1"
}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Claude Usage Monitor - Installer       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────
# Step 1: Python 확인
# ─────────────────────────────────────────────
print_step "Python 환경 확인..."

if ! command -v python3 &> /dev/null; then
    print_error "python3이 설치되어 있지 않습니다."
    echo "  brew install python3 으로 설치해주세요."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
print_done "Python 확인: $PYTHON_VERSION"

# ─────────────────────────────────────────────
# Step 2: SQLite 데이터베이스 초기화
# ─────────────────────────────────────────────
print_step "SQLite 데이터베이스 초기화..."

mkdir -p "$DB_DIR"

if [ -f "$DB_PATH" ]; then
    print_warn "기존 데이터베이스가 있습니다: $DB_PATH"
    read -p "  기존 DB를 유지하고 스키마만 업데이트할까요? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        BACKUP_PATH="$DB_PATH.backup.$(date +%Y%m%d%H%M%S)"
        cp "$DB_PATH" "$BACKUP_PATH"
        print_done "백업 생성: $BACKUP_PATH"
        rm "$DB_PATH"
    fi
fi

sqlite3 "$DB_PATH" < "$INSTALL_DIR/sql/schema.sql"
print_done "데이터베이스 초기화 완료: $DB_PATH"

# ─────────────────────────────────────────────
# Step 3: PYTHONSTARTUP Hook 설정
# ─────────────────────────────────────────────
print_step "PYTHONSTARTUP Hook 설정..."

cat > "$STARTUP_SCRIPT" << 'PYEOF'
"""
Claude Usage Monitor - PYTHONSTARTUP Hook
Anthropic/OpenAI API 호출을 자동으로 캡처합니다.
"""
import importlib
import sys

def _install_usage_hooks():
    """API 클라이언트에 사용량 추적 Hook을 설치."""
    import json
    import sqlite3
    from pathlib import Path
    from functools import wraps

    DB_PATH = Path.home() / ".claude-usage-monitor" / "usage.db"
    if not DB_PATH.exists():
        return

    def _record(provider, model, input_tokens, output_tokens, cost):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                "INSERT INTO prompts (provider, model, input_tokens, output_tokens, cost_usd) VALUES (?, ?, ?, ?, ?)",
                (provider, model, input_tokens, output_tokens, cost),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    # Anthropic Hook
    try:
        import anthropic
        _orig_create = anthropic.resources.messages.Messages.create

        @wraps(_orig_create)
        def _hooked_anthropic_create(self, *args, **kwargs):
            response = _orig_create(self, *args, **kwargs)
            try:
                usage = response.usage
                model = response.model
                input_t = usage.input_tokens
                output_t = usage.output_tokens
                # 간단한 비용 계산
                PRICES = {
                    "claude-opus-4-6": (15.0, 75.0),
                    "claude-sonnet-4-6": (3.0, 15.0),
                    "claude-haiku-4-5-20251001": (0.80, 4.0),
                }
                price = PRICES.get(model, (3.0, 15.0))
                cost = (input_t / 1e6) * price[0] + (output_t / 1e6) * price[1]
                _record("anthropic", model, input_t, output_t, round(cost, 6))
            except Exception:
                pass
            return response

        anthropic.resources.messages.Messages.create = _hooked_anthropic_create
    except (ImportError, AttributeError):
        pass

    # OpenAI Hook
    try:
        import openai
        _orig_openai_create = openai.resources.chat.completions.Completions.create

        @wraps(_orig_openai_create)
        def _hooked_openai_create(self, *args, **kwargs):
            response = _orig_openai_create(self, *args, **kwargs)
            try:
                usage = response.usage
                model = response.model
                input_t = usage.prompt_tokens
                output_t = usage.completion_tokens
                PRICES = {
                    "gpt-4o": (2.50, 10.0),
                    "gpt-4o-mini": (0.15, 0.60),
                    "gpt-4-turbo": (10.0, 30.0),
                }
                price = PRICES.get(model, (2.50, 10.0))
                cost = (input_t / 1e6) * price[0] + (output_t / 1e6) * price[1]
                _record("openai", model, input_t, output_t, round(cost, 6))
            except Exception:
                pass
            return response

        openai.resources.chat.completions.Completions.create = _hooked_openai_create
    except (ImportError, AttributeError):
        pass

try:
    _install_usage_hooks()
except Exception:
    pass
PYEOF

print_done "PYTHONSTARTUP 스크립트 생성: $STARTUP_SCRIPT"

# 쉘 프로파일에 PYTHONSTARTUP 추가
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_RC="$HOME/.bash_profile"
fi

if [ -n "$SHELL_RC" ]; then
    EXPORT_LINE="export PYTHONSTARTUP=\"$STARTUP_SCRIPT\""
    if grep -q "claude-usage-monitor" "$SHELL_RC" 2>/dev/null; then
        print_warn "PYTHONSTARTUP이 이미 $SHELL_RC 에 설정되어 있습니다."
    else
        echo "" >> "$SHELL_RC"
        echo "# Claude Usage Monitor - API 사용량 자동 추적" >> "$SHELL_RC"
        echo "$EXPORT_LINE" >> "$SHELL_RC"
        print_done "PYTHONSTARTUP 추가됨: $SHELL_RC"
    fi
else
    print_warn "쉘 설정 파일을 찾을 수 없습니다. 수동으로 추가해주세요:"
    echo "  export PYTHONSTARTUP=\"$STARTUP_SCRIPT\""
fi

# ─────────────────────────────────────────────
# Step 4: xbar 플러그인 복사
# ─────────────────────────────────────────────
print_step "xbar 메뉴바 플러그인 설정..."

MENUBAR_SRC="$INSTALL_DIR/menubar/claude-usage-monitor.10m.py"

if [ -f "$MENUBAR_SRC" ]; then
    if [ -d "$XBAR_PLUGIN_DIR" ]; then
        cp "$MENUBAR_SRC" "$XBAR_PLUGIN_DIR/"
        chmod +x "$XBAR_PLUGIN_DIR/claude-usage-monitor.10m.py"
        print_done "xbar 플러그인 복사 완료: $XBAR_PLUGIN_DIR/"
    else
        print_warn "xbar 플러그인 디렉토리가 없습니다."
        echo "  xbar를 설치하려면: brew install --cask xbar"
        echo "  설치 후 수동 복사:"
        echo "  cp $MENUBAR_SRC \"$XBAR_PLUGIN_DIR/\""
    fi
else
    print_warn "메뉴바 플러그인 파일을 찾을 수 없습니다: $MENUBAR_SRC"
fi

# ─────────────────────────────────────────────
# Step 5: hook.py 실행 권한
# ─────────────────────────────────────────────
print_step "스크립트 실행 권한 설정..."
chmod +x "$HOOK_PATH" 2>/dev/null && print_done "hook.py 실행 권한 설정 완료"
chmod +x "$MENUBAR_SRC" 2>/dev/null && print_done "메뉴바 플러그인 실행 권한 설정 완료"

# ─────────────────────────────────────────────
# 완료
# ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          설치가 완료되었습니다!            ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  DB 경로:     $DB_PATH"
echo "  Hook 경로:   $STARTUP_SCRIPT"
echo "  xbar 플러그인: $XBAR_PLUGIN_DIR/claude-usage-monitor.10m.py"
echo ""
echo "  새 터미널을 열거나 다음을 실행하세요:"
echo "    source $SHELL_RC"
echo ""
echo "  테스트:"
echo "    python3 examples/test_api.py"
echo ""
