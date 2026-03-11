# Claude Usage Monitor

macOS 메뉴바에서 Claude API 사용량을 실시간으로 추적하는 앱입니다.

## 주요 기능

- **Claude Code 자동 연동**: Stop Hook으로 세션 종료 시 자동 사용량 기록
- **10분 자동 갱신**: xbar 메뉴바에서 토큰 사용량 실시간 확인
- **원클릭 설치**: `.command` 파일 더블클릭으로 자동 설치
- **SQLite 저장**: 모든 API 호출 기록을 로컬 SQLite DB에 저장
- **월 예산 관리**: 예산 설정 및 사용률에 따른 색상 알림 (초록/주황/빨강)

## 작동 방식

```
Claude Code 세션 종료
  → Stop Hook 실행 (claude-code-hook.py)
  → transcript 파일에서 토큰 사용량 파싱
  → SQLite DB에 기록
  → xbar 메뉴바에서 실시간 표시 (💬 $12.34/200)
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

- Claude Code를 사용하면 세션 종료 시 **자동으로 사용량 기록**
- macOS 메뉴바에 `💬 $0.00/200` 형태로 표시
- 클릭하면 모델별 상세 사용량 확인 가능
- **10분마다 자동 갱신**

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
