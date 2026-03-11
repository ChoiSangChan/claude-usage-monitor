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
CONFIG_DIR="$HOME/.claude-usage-monitor"
CONFIG_PATH="$CONFIG_DIR/config.json"
XBAR_PLUGIN_DIR="$HOME/Library/Application Support/xbar/plugins"

clear
echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║                                                      ║"
echo "  ║   💬 Claude Usage Monitor                            ║"
echo "  ║   원클릭 설치 프로그램 v3.0                            ║"
echo "  ║                                                      ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  이 프로그램은 다음을 자동으로 설치합니다:"
echo ""
echo -e "    ${GREEN}✦${NC} ~/.claude/projects/ JSONL 파일에서 사용량 자동 집계"
echo -e "    ${GREEN}✦${NC} macOS 메뉴바에 사용량 & 예산 실시간 표시"
echo -e "    ${GREEN}✦${NC} 10분마다 자동 갱신"
echo ""
echo -e "  ${YELLOW}설치를 시작하려면 Enter를 누르세요. (취소: Ctrl+C)${NC}"
read -r

# ─────────────────────────────────────────────────────
# Step 1: macOS 확인
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [1/4] 시스템 확인${NC}"
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

if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}  ⚠ Python3가 설치되어 있지 않습니다.${NC}"
    if command -v brew &> /dev/null; then
        brew install python3
    else
        echo -e "${RED}  ✖ Python3과 Homebrew가 없습니다.${NC}"
        echo "  https://www.python.org/downloads/ 에서 Python을 먼저 설치해주세요."
        echo "  아무 키나 누르면 종료합니다."
        read -n 1
        exit 1
    fi
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}  ✔ $PYTHON_VERSION${NC}"

# ─────────────────────────────────────────────────────
# Step 2: 프로젝트 다운로드
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [2/4] 프로젝트 다운로드${NC}"
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
# Step 3: 설정 파일 생성
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [3/4] 설정${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_PATH" ]; then
    echo -e "${GREEN}  ✔ 기존 설정 유지: $CONFIG_PATH${NC}"
else
    cat > "$CONFIG_PATH" << 'JSONEOF'
{
    "monthly_budget_usd": 100.0
}
JSONEOF
    echo -e "${GREEN}  ✔ 설정 파일 생성: $CONFIG_PATH${NC}"
fi

echo -e "     월 예산을 변경하려면: $CONFIG_PATH 를 편집하세요"

# ─────────────────────────────────────────────────────
# Step 4: xbar 메뉴바 플러그인
# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  [4/4] 메뉴바 플러그인 설정${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MENUBAR_SRC="$INSTALL_DIR/menubar/claude-usage-monitor.10m.py"
chmod +x "$MENUBAR_SRC"

if [ -d "$XBAR_PLUGIN_DIR" ]; then
    # 기존 중복 플러그인 제거
    rm -f "$XBAR_PLUGIN_DIR/claude-usage-monitor.5m.py" 2>/dev/null
    cp "$MENUBAR_SRC" "$XBAR_PLUGIN_DIR/"
    chmod +x "$XBAR_PLUGIN_DIR/claude-usage-monitor.10m.py"
    echo -e "${GREEN}  ✔ xbar 플러그인 설치 완료${NC}"
else
    echo -e "${YELLOW}  ⚠ xbar가 아직 설치되지 않았습니다.${NC}"
    echo ""
    echo -e "  xbar를 설치하려면 터미널에서:"
    echo -e "    ${BOLD}brew install --cask xbar${NC}"
    echo ""
    echo -e "  설치 후 이 파일을 다시 실행하면 자동으로 플러그인이 설치됩니다."
fi

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
echo -e "  ${BOLD}작동 방식:${NC}"
echo -e "    ${CYAN}✦${NC} ~/.claude/projects/ 의 JSONL transcript 파일을 직접 읽어"
echo -e "      Claude Code 사용량을 자동 집계합니다."
echo -e "    ${CYAN}✦${NC} Hook이나 API 키 없이 동작합니다."
echo -e "    ${CYAN}✦${NC} 10분마다 xbar 메뉴바에서 자동 갱신됩니다."
echo ""
echo -e "  ${BOLD}참고:${NC}"
echo -e "    xbar가 실행 중이면 메뉴바의 xbar 아이콘 > Refresh All을 클릭하세요."
echo ""
echo -e "  ${YELLOW}아무 키나 누르면 이 창이 닫힙니다.${NC}"
read -n 1
