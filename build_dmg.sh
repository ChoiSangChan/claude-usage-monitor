#!/bin/bash
#
# Claude Usage Monitor - DMG 빌드 스크립트
# .app 번들을 생성하고 DMG 파일로 패키징합니다.
#
# 사용법:
#   chmod +x build_dmg.sh
#   ./build_dmg.sh
#
# 필수 조건:
#   - macOS 10.15+
#   - Python 3.8+
#   - pip install py2app rumps
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 설정
APP_NAME="Claude Usage Monitor"
APP_BUNDLE="$APP_NAME.app"
DMG_NAME="ClaudeUsageMonitor"
VERSION="1.0.0"
DMG_FILENAME="${DMG_NAME}-${VERSION}.dmg"
BUILD_DIR="build"
DIST_DIR="dist"
DMG_DIR="dmg_staging"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  ▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_done() {
    echo -e "${GREEN}  ✔ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✖ $1${NC}"
}

cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Claude Usage Monitor - DMG Builder           ║${NC}"
echo -e "${CYAN}║     Version: ${VERSION}                               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────
# Step 0: 사전 조건 확인
# ─────────────────────────────────────────────
print_step "사전 조건 확인"

# Python
if ! command -v python3 &> /dev/null; then
    print_error "python3이 설치되어 있지 않습니다."
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
print_done "Python: $PYTHON_VERSION"

# pip 패키지 확인
python3 -c "import rumps" 2>/dev/null || {
    print_warn "rumps가 없습니다. 설치 중..."
    pip3 install rumps
}
print_done "rumps 확인"

python3 -c "import py2app" 2>/dev/null || {
    print_warn "py2app이 없습니다. 설치 중..."
    pip3 install py2app
}
print_done "py2app 확인"

# macOS 확인
if [[ "$(uname)" != "Darwin" ]]; then
    print_error "이 스크립트는 macOS에서만 실행할 수 있습니다."
    print_warn "현재 OS: $(uname)"
    echo ""
    echo "  Linux/Windows에서는 다음 명령으로 테스트할 수 있습니다:"
    echo "    python3 app/claude_usage_monitor.py"
    exit 1
fi
print_done "macOS 확인: $(sw_vers -productVersion)"

# ─────────────────────────────────────────────
# Step 1: 정리
# ─────────────────────────────────────────────
print_step "이전 빌드 정리"

rm -rf "$BUILD_DIR" "$DIST_DIR" "$DMG_DIR" "$DMG_FILENAME"
print_done "빌드 디렉토리 정리 완료"

# ─────────────────────────────────────────────
# Step 2: 아이콘 생성
# ─────────────────────────────────────────────
print_step "앱 아이콘 생성"

if [ ! -f "app/resources/AppIcon.icns" ]; then
    python3 app/resources/create_icon.py
else
    print_done "아이콘 이미 존재: app/resources/AppIcon.icns"
fi

# ─────────────────────────────────────────────
# Step 3: py2app으로 .app 번들 빌드
# ─────────────────────────────────────────────
print_step ".app 번들 빌드 (py2app)"

python3 setup.py py2app --dist-dir "$DIST_DIR" 2>&1 | while IFS= read -r line; do
    echo "    $line"
done

if [ ! -d "$DIST_DIR/$APP_BUNDLE" ]; then
    print_error ".app 번들 생성에 실패했습니다."
    exit 1
fi
print_done ".app 번들 생성 완료: $DIST_DIR/$APP_BUNDLE"

# .app 크기 확인
APP_SIZE=$(du -sh "$DIST_DIR/$APP_BUNDLE" | cut -f1)
print_done "앱 크기: $APP_SIZE"

# ─────────────────────────────────────────────
# Step 4: PYTHONSTARTUP Hook 스크립트 포함
# ─────────────────────────────────────────────
print_step "Hook 스크립트 & 스키마 번들링"

RESOURCES_IN_APP="$DIST_DIR/$APP_BUNDLE/Contents/Resources"
mkdir -p "$RESOURCES_IN_APP/scripts"
mkdir -p "$RESOURCES_IN_APP/sql"

cp scripts/hook.py "$RESOURCES_IN_APP/scripts/"
cp sql/schema.sql "$RESOURCES_IN_APP/sql/"
cp install.sh "$RESOURCES_IN_APP/"

print_done "리소스 번들링 완료"

# ─────────────────────────────────────────────
# Step 5: DMG 스테이징
# ─────────────────────────────────────────────
print_step "DMG 스테이징"

mkdir -p "$DMG_DIR"

# .app 복사
cp -R "$DIST_DIR/$APP_BUNDLE" "$DMG_DIR/"

# Applications 심볼릭 링크 (드래그 앤 드롭 설치용)
ln -sf /Applications "$DMG_DIR/Applications"

# README 생성
cat > "$DMG_DIR/README.txt" << 'EOF'
╔══════════════════════════════════════════════════╗
║          Claude Usage Monitor                     ║
║          macOS LLM API 사용량 추적기               ║
╚══════════════════════════════════════════════════╝

설치 방법:
  1. "Claude Usage Monitor.app"을 "Applications" 폴더로 드래그하세요.
  2. Applications에서 앱을 실행하세요.
  3. 최초 실행 시 "시스템 환경설정 > 보안 및 개인정보"에서 허용해주세요.

Hook 설정 (API 자동 캡처):
  앱 실행 후 터미널에서:
    /Applications/Claude\ Usage\ Monitor.app/Contents/Resources/install.sh

주요 기능:
  • 10분마다 자동 사용량 갱신
  • 35개 이상 LLM 모델 지원
  • 월 예산 설정 및 알림
  • 모델별 상세 분석

라이선스: MIT
EOF

print_done "스테이징 완료"

# ─────────────────────────────────────────────
# Step 6: DMG 생성
# ─────────────────────────────────────────────
print_step "DMG 파일 생성"

# create-dmg가 있으면 사용 (예쁜 DMG)
if command -v create-dmg &> /dev/null; then
    print_done "create-dmg 발견 - 커스텀 DMG 생성"

    create-dmg \
        --volname "$APP_NAME" \
        --volicon "app/resources/AppIcon.icns" \
        --window-pos 200 120 \
        --window-size 660 400 \
        --icon-size 100 \
        --icon "$APP_BUNDLE" 180 190 \
        --icon "Applications" 480 190 \
        --hide-extension "$APP_BUNDLE" \
        --app-drop-link 480 190 \
        --background-color "#f0f0f0" \
        "$DMG_FILENAME" \
        "$DMG_DIR/" \
    || {
        print_warn "create-dmg 실패. hdiutil로 대체합니다."
        hdiutil create \
            -volname "$APP_NAME" \
            -srcfolder "$DMG_DIR" \
            -ov \
            -format UDZO \
            -imagekey zlib-level=9 \
            "$DMG_FILENAME"
    }
else
    print_warn "create-dmg 미설치. hdiutil로 기본 DMG 생성"
    echo "    (더 예쁜 DMG를 원하시면: brew install create-dmg)"

    hdiutil create \
        -volname "$APP_NAME" \
        -srcfolder "$DMG_DIR" \
        -ov \
        -format UDZO \
        -imagekey zlib-level=9 \
        "$DMG_FILENAME"
fi

if [ ! -f "$DMG_FILENAME" ]; then
    print_error "DMG 생성에 실패했습니다."
    exit 1
fi

DMG_SIZE=$(du -sh "$DMG_FILENAME" | cut -f1)
print_done "DMG 생성 완료!"

# ─────────────────────────────────────────────
# Step 7: 정리
# ─────────────────────────────────────────────
print_step "정리"

rm -rf "$BUILD_DIR" "$DMG_DIR"
print_done "임시 파일 정리 완료"
echo "  (dist/ 디렉토리는 유지됩니다)"

# ─────────────────────────────────────────────
# 완료
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          DMG 빌드 완료!                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}DMG 파일:${NC}  $SCRIPT_DIR/$DMG_FILENAME"
echo -e "  ${CYAN}파일 크기:${NC}  $DMG_SIZE"
echo -e "  ${CYAN}앱 번들:${NC}   $SCRIPT_DIR/$DIST_DIR/$APP_BUNDLE"
echo ""
echo -e "  ${YELLOW}배포 전 테스트:${NC}"
echo -e "    open $DMG_FILENAME"
echo ""
echo -e "  ${YELLOW}코드 서명 (선택):${NC}"
echo -e "    codesign --deep --force --sign \"Developer ID Application: YOUR_NAME\" \"$DIST_DIR/$APP_BUNDLE\""
echo ""
