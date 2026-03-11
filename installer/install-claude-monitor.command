#!/bin/bash
#
# ╔══════════════════════════════════════════════════════╗
# ║  Claude Usage Monitor - 원클릭 설치 프로그램           ║
# ║  이 파일을 더블클릭하면 자동으로 설치됩니다.              ║
# ╚══════════════════════════════════════════════════════╝
#
# 사용법:
#   방법 1: 이 파일(.command)을 Finder에서 더블클릭
#   방법 2: 터미널에서 실행: bash install-claude-monitor.command
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 설정
REPO_URL="https://github.com/ChoiSangChan/claude-usage-monitor.git"
INSTALL_DIR="$HOME/claude-usage-monitor"
DB_DIR="$HOME/.claude-usage-monitor"
DB_PATH="$DB_DIR/usage.db"
XBAR_PLUGIN_DIR="$HOME/Library/Application Support/xbar/plugins"
STARTUP_SCRIPT="$DB_DIR/pythonstartup.py"

clear
echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║                                                      ║"
echo "  ║   💬 Claude Usage Monitor                            ║"
echo "  ║   원클릭 설치 프로그램                                  ║"
echo "  ║                                                      ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  이 프로그램은 다음을 자동으로 설치합니다:"
echo ""
echo -e "    ${GREEN}✦${NC} LLM API 사용량 자동 추적 (Anthropic, OpenAI)"
echo -e "    ${GREEN}✦${NC} macOS 메뉴바에 사용량 & 예산 실시간 표시"
echo -e "    ${GREEN}✦${NC} 10분마다 자동 갱신"
echo -e "    ${GREEN}✦${NC} 35개+ AI 모델 지원"
echo ""
echo -e "  ${YELLOW}설치를 시작하려면 Enter를 누르세요. (취소: Ctrl+C)${NC}"
read -r

# ─────────────────────────────────────────────────────
# Step 1: macOS 확인
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [1/6] 시스템 확인${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}  ✖ 이 프로그램은 macOS에서만 사용할 수 있습니다.${NC}"
    echo "  현재 OS: $(uname)"
    echo ""
    echo "  아무 키나 누르면 종료합니다."
    read -n 1
    exit 1
fi
echo -e "${GREEN}  ✔ macOS $(sw_vers -productVersion) 확인${NC}"

# ─────────────────────────────────────────────────────
# Step 2: Python 확인
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [2/6] Python 확인${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}  ⚠ Python3가 설치되어 있지 않습니다.${NC}"
    echo ""
    echo "  자동으로 설치를 시도합니다..."

    if command -v brew &> /dev/null; then
        brew install python3
    else
        echo -e "${RED}  ✖ Homebrew도 설치되어 있지 않습니다.${NC}"
        echo ""
        echo "  다음 중 하나를 먼저 설치해주세요:"
        echo "    1. https://www.python.org/downloads/ 에서 Python 다운로드"
        echo "    2. 또는 터미널에서:"
        echo '       /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        echo "       brew install python3"
        echo ""
        echo "  설치 후 이 파일을 다시 실행해주세요."
        echo "  아무 키나 누르면 종료합니다."
        read -n 1
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}  ✔ $PYTHON_VERSION${NC}"

# ─────────────────────────────────────────────────────
# Step 3: 프로젝트 다운로드
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [3/6] 프로젝트 다운로드${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}  ⚠ 기존 설치가 있습니다: $INSTALL_DIR${NC}"
    echo -e "  업데이트합니다..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || git pull 2>/dev/null || true
    echo -e "${GREEN}  ✔ 업데이트 완료${NC}"
else
    if command -v git &> /dev/null; then
        echo "  GitHub에서 다운로드 중..."
        git clone "$REPO_URL" "$INSTALL_DIR" 2>&1 | tail -2
        echo -e "${GREEN}  ✔ 다운로드 완료: $INSTALL_DIR${NC}"
    else
        echo "  git이 없습니다. ZIP으로 다운로드합니다..."
        cd /tmp
        curl -sL "https://github.com/ChoiSangChan/claude-usage-monitor/archive/refs/heads/main.zip" -o claude-monitor.zip
        unzip -qo claude-monitor.zip
        mv claude-usage-monitor-main "$INSTALL_DIR"
        rm claude-monitor.zip
        echo -e "${GREEN}  ✔ 다운로드 완료: $INSTALL_DIR${NC}"
    fi
fi

cd "$INSTALL_DIR"

# ─────────────────────────────────────────────────────
# Step 4: 데이터베이스 설정
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [4/6] 데이터베이스 설정${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

mkdir -p "$DB_DIR"

if [ -f "$DB_PATH" ]; then
    echo -e "${GREEN}  ✔ 기존 데이터베이스 유지: $DB_PATH${NC}"
    # 스키마 업데이트 (기존 데이터 보존)
    sqlite3 "$DB_PATH" < "$INSTALL_DIR/sql/schema.sql" 2>/dev/null || true
else
    sqlite3 "$DB_PATH" < "$INSTALL_DIR/sql/schema.sql"
    echo -e "${GREEN}  ✔ 데이터베이스 생성 완료${NC}"
fi

# ─────────────────────────────────────────────────────
# Step 5: API 자동 추적 Hook 설정
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [5/6] API 자동 추적 설정${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# PYTHONSTARTUP Hook 생성
cat > "$STARTUP_SCRIPT" << 'PYEOF'
"""
Claude Usage Monitor - PYTHONSTARTUP Hook
Anthropic/OpenAI API 호출을 자동으로 캡처합니다.
"""
import importlib
import sys

def _install_usage_hooks():
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

echo -e "${GREEN}  ✔ API 추적 Hook 생성 완료${NC}"

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
        echo -e "${GREEN}  ✔ PYTHONSTARTUP 이미 설정됨${NC}"
    else
        echo "" >> "$SHELL_RC"
        echo "# Claude Usage Monitor - API 사용량 자동 추적" >> "$SHELL_RC"
        echo "$EXPORT_LINE" >> "$SHELL_RC"
        echo -e "${GREEN}  ✔ PYTHONSTARTUP 설정 완료 ($SHELL_RC)${NC}"
    fi
fi

# ─────────────────────────────────────────────────────
# Step 6: xbar 메뉴바 플러그인
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [6/6] 메뉴바 플러그인 설정${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MENUBAR_SRC="$INSTALL_DIR/menubar/claude-usage-monitor.10m.py"

if [ -d "$XBAR_PLUGIN_DIR" ]; then
    cp "$MENUBAR_SRC" "$XBAR_PLUGIN_DIR/"
    chmod +x "$XBAR_PLUGIN_DIR/claude-usage-monitor.10m.py"
    echo -e "${GREEN}  ✔ xbar 플러그인 설치 완료${NC}"
    echo -e "     10분마다 자동으로 사용량이 갱신됩니다."
else
    echo -e "${YELLOW}  ⚠ xbar가 아직 설치되지 않았습니다.${NC}"
    echo ""
    echo -e "  xbar를 설치하려면 터미널에서:"
    echo -e "    ${BOLD}brew install --cask xbar${NC}"
    echo ""
    echo -e "  설치 후 이 파일을 다시 실행하면 자동으로 플러그인이 설치됩니다."
fi

# 실행 권한
chmod +x "$INSTALL_DIR/scripts/hook.py" 2>/dev/null
chmod +x "$MENUBAR_SRC" 2>/dev/null

# ─────────────────────────────────────────────────────
# 완료!
# ─────────────────────────────────────────────────────
echo ""
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║                                                      ║"
echo "  ║   🎉 설치가 완료되었습니다!                            ║"
echo "  ║                                                      ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  ${BOLD}설치 정보:${NC}"
echo -e "    📂 프로젝트:    $INSTALL_DIR"
echo -e "    💾 데이터베이스: $DB_PATH"
echo -e "    🔗 Hook:       $STARTUP_SCRIPT"
echo ""
echo -e "  ${BOLD}다음 할 일:${NC}"
echo -e "    ${CYAN}1.${NC} 터미널을 닫고 다시 열어주세요 (또는 source $SHELL_RC)"
echo -e "    ${CYAN}2.${NC} xbar 앱을 실행해주세요 (Applications > xbar)"
echo -e "    ${CYAN}3.${NC} 이제 Python에서 API 호출하면 자동으로 추적됩니다!"
echo ""
echo -e "  ${BOLD}테스트:${NC}"
echo -e "    python3 $INSTALL_DIR/examples/test_api.py"
echo ""
echo -e "  ${YELLOW}아무 키나 누르면 이 창이 닫힙니다.${NC}"
read -n 1
