# Claude Usage Monitor

macOS 메뉴바에서 Claude API 사용량을 실시간으로 추적하는 앱입니다.

## 주요 기능

- **Anthropic Admin API 연동**: 실제 청구액을 자동으로 조회
- **Claude Code JSONL 스캔**: 로컬 transcript에서 API 사용량 추정
- **GUI API Key 설정**: 메뉴바에서 클릭 한 번으로 Admin API Key 등록
- **10분 자동 갱신**: xbar 메뉴바에서 비용 실시간 확인
- **캐시 토큰 가격 보정**: cache_write 1.25x, cache_read 0.1x 적용
- **원클릭 설치**: `.command` 파일 더블클릭으로 자동 설치

## 작동 방식

```
메뉴바 표시: 💬 $107.23
  ├─ 💰 API Monthly Limit — Anthropic Admin API 실제 청구액 (자동 조회)
  └─ 💻 Claude Code API 사용 추정 — 로컬 JSONL 기반 비용 추정

데이터 소스:
  1. Anthropic Admin API (cost_report) → 실제 청구액 (5분 캐시)
  2. ~/.claude/projects/**/*.jsonl → Claude Code 사용량 추정
```

## 설치 방법

### 방법 1: 원클릭 설치 (권장)

1. [installer/install-claude-monitor.command](installer/install-claude-monitor.command) 파일을 다운로드
2. Finder에서 **더블클릭**
3. 화면 안내를 따르면 끝!

> "개발자를 확인할 수 없습니다" 경고가 나오면:
> 시스템 설정 > 개인정보 보호 및 보안 > 아래쪽 "확인 없이 열기" 클릭

### 방법 2: 터미널에서 한 줄 설치

```bash
curl -sL https://raw.githubusercontent.com/ChoiSangChan/claude-usage-monitor/main/installer/install-claude-monitor.command | bash
```

### 방법 3: 수동 설치

```bash
git clone https://github.com/ChoiSangChan/claude-usage-monitor.git
cd claude-usage-monitor
bash install.sh
```

## 설치 후 사용법

설치 후에는 **아무것도 안 해도 됩니다!**

- macOS 메뉴바에 `💬 $0.00` 형태로 현재 월 사용액 표시
- 클릭하면 모델별 상세 사용량 확인 가능
- **10분마다 자동 갱신**

### Admin API Key 등록 (선택)

실제 청구액을 조회하려면 Anthropic Admin API Key가 필요합니다:

1. 메뉴바에서 `💬` 아이콘 클릭
2. `⚙️ 설정` → `🔑 API Key 등록하기` 클릭
3. Admin API Key (`sk-ant-admin01-...`) 입력 후 저장

> Admin API Key는 [Anthropic Console](https://console.anthropic.com/) → Settings → Admin API Keys에서 발급받을 수 있습니다.

## 프로젝트 구조

```
claude-usage-monitor/
├── installer/
│   └── install-claude-monitor.command  # 원클릭 설치 파일 (더블클릭!)
├── scripts/
│   ├── claude-code-hook.py             # Claude Code Stop Hook (핵심)
│   └── hook.py                         # 범용 API Hook
├── menubar/
│   └── claude-usage-monitor.10m.py     # xbar 메뉴바 플러그인
├── sql/
│   └── schema.sql                      # 데이터베이스 스키마
├── app/
│   ├── claude_usage_monitor.py         # 독립 실행형 메뉴바 앱 (rumps)
│   └── resources/
│       └── create_icon.py              # 앱 아이콘 생성기
├── setup.py                            # py2app 빌드 설정
├── build_dmg.sh                        # DMG 빌드 스크립트
├── Makefile                            # 빌드 명령어
└── README.md
```

## 라이선스

MIT License
