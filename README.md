# Claude Usage Monitor

macOS 메뉴바에서 LLM API 사용량을 실시간으로 추적하는 앱입니다.

## 주요 기능

- **10분 자동 갱신**: 토큰 사용량을 10분마다 자동으로 최신화
- **원클릭 설치**: `.command` 파일 더블클릭으로 자동 설치
- **자동 사용량 추적**: Python Hook을 통해 Anthropic, OpenAI API 호출을 자동 캡처
- **SQLite 저장**: 모든 API 호출 기록을 로컬 SQLite DB에 저장
- **월 예산 관리**: 예산 설정 및 사용률에 따른 색상 알림 (초록/주황/빨강)
- **35개 모델 지원**: Anthropic, OpenAI, Google, Meta, Mistral

## 지원 API

| Provider | 모델 예시 |
|----------|-----------|
| Anthropic | Claude Opus 4.6, Sonnet 4.6, Haiku 4.5 |
| OpenAI | GPT-4o, GPT-4, GPT-3.5, o1/o3 |
| Google | Gemini 2.0 Flash/Pro |
| Meta | Llama 3.1 시리즈 |
| Mistral | Mistral Large |

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

- Python에서 Anthropic/OpenAI API를 호출하면 **자동으로 사용량 기록**
- macOS 메뉴바에 `💬 $0/100` 형태로 표시
- 클릭하면 모델별 상세 사용량 확인 가능
- **10분마다 자동 갱신**

## 빌드 명령어 (개발자용)

```bash
make help     # 전체 명령어 보기
make deps     # 의존성 설치
make run      # 개발 모드 실행
make app      # .app 번들 빌드
make dmg      # DMG 파일 빌드
make test     # 테스트 실행
make clean    # 빌드 산출물 정리
```

## 프로젝트 구조

```
claude-usage-monitor/
├── installer/
│   └── install-claude-monitor.command  # 원클릭 설치 파일 (더블클릭!)
├── app/
│   ├── claude_usage_monitor.py         # 독립 실행형 메뉴바 앱 (rumps)
│   └── resources/
│       └── create_icon.py              # 앱 아이콘 생성기
├── scripts/
│   └── hook.py                         # API 호출 자동 캡처 Hook
├── sql/
│   └── schema.sql                      # 데이터베이스 스키마
├── menubar/
│   └── claude-usage-monitor.10m.py     # xbar 메뉴바 플러그인
├── examples/
│   └── test_api.py                     # 테스트 스위트
├── setup.py                            # py2app 빌드 설정
├── build_dmg.sh                        # DMG 빌드 스크립트
├── Makefile                            # 빌드 명령어
├── requirements.txt                    # Python 의존성
├── INSTALL_GUIDE.md                    # 상세 설치 가이드
└── README.md
```

## 라이선스

MIT License
