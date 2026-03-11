# Claude Usage Monitor

macOS 메뉴바에서 LLM API 사용량을 실시간으로 추적하는 앱입니다.

## 주요 기능

- **10분 자동 갱신**: 토큰 사용량을 10분마다 자동으로 최신화
- **독립 실행형 앱**: DMG로 설치하는 네이티브 macOS 메뉴바 앱
- **자동 사용량 추적**: Python Hook을 통해 Anthropic, OpenAI API 호출을 자동 캡처
- **SQLite 저장**: 모든 API 호출 기록을 로컬 SQLite DB에 저장
- **월 예산 관리**: 예산 설정 및 사용률에 따른 색상 알림
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

### 방법 1: DMG 설치 (권장)

1. [Releases](https://github.com/ChoiSangChan/claude-usage-monitor/releases)에서 DMG 파일 다운로드
2. DMG를 열고 앱을 Applications 폴더로 드래그
3. 앱 실행

```bash
# Hook 설정 (API 자동 캡처)
/Applications/Claude\ Usage\ Monitor.app/Contents/Resources/install.sh
```

### 방법 2: 소스에서 직접 빌드

```bash
git clone https://github.com/ChoiSangChan/claude-usage-monitor.git
cd claude-usage-monitor

# 의존성 설치
pip install -r requirements.txt

# DMG 빌드
make dmg

# 또는 개발 모드로 실행
make run
```

### 방법 3: xbar 플러그인 (레거시)

```bash
./install.sh
```

## 빌드 명령어

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
├── app/
│   ├── claude_usage_monitor.py   # 독립 실행형 메뉴바 앱 (rumps)
│   └── resources/
│       └── create_icon.py        # 앱 아이콘 생성기
├── scripts/
│   └── hook.py                   # API 호출 자동 캡처 Hook
├── sql/
│   └── schema.sql                # 데이터베이스 스키마
├── menubar/
│   └── claude-usage-monitor.10m.py  # xbar 플러그인 (레거시)
├── examples/
│   └── test_api.py               # 테스트 스위트
├── setup.py                      # py2app 빌드 설정
├── build_dmg.sh                  # DMG 빌드 스크립트
├── Makefile                      # 빌드 명령어
├── requirements.txt              # Python 의존성
└── README.md
```

## 라이선스

MIT License
