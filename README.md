# Claude Usage Monitor

macOS 메뉴바에서 LLM API 사용량을 실시간으로 추적하는 앱입니다.

## 주요 기능

- **자동 사용량 추적**: Python Hook을 통해 Anthropic, OpenAI API 호출을 자동 캡처
- **SQLite 저장**: 모든 API 호출 기록을 로컬 SQLite DB에 저장
- **메뉴바 앱**: macOS 메뉴바에서 사용량 확인

## 지원 API

| Provider | 모델 예시 |
|----------|-----------|
| Anthropic | Claude Opus, Sonnet, Haiku |
| OpenAI | GPT-4o, GPT-4, GPT-3.5 |

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/claude-usage-monitor.git
cd claude-usage-monitor
```

### 2. Python 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 초기화

```bash
sqlite3 ~/.claude-usage-monitor/usage.db < sql/schema.sql
```

### 4. Hook 설정

API 호출을 자동으로 캡처하려면 hook을 활성화합니다:

```bash
python scripts/hook.py --install
```

## 사용 방법

### Hook을 통한 자동 추적

Hook이 설치되면 Anthropic/OpenAI API 호출 시 자동으로 사용량이 기록됩니다.

```bash
# Hook 실행 (수동)
python scripts/hook.py

# 기록 확인
sqlite3 ~/.claude-usage-monitor/usage.db "SELECT * FROM prompts ORDER BY created_at DESC LIMIT 10;"
```

### 데이터 확인

```bash
# 오늘 사용량 요약
sqlite3 ~/.claude-usage-monitor/usage.db \
  "SELECT provider, model, SUM(input_tokens) as input, SUM(output_tokens) as output, SUM(cost_usd) as cost FROM prompts WHERE date(created_at) = date('now') GROUP BY provider, model;"
```

## 프로젝트 구조

```
claude-usage-monitor/
├── scripts/
│   └── hook.py          # API 호출 자동 캡처 Hook
├── sql/
│   └── schema.sql       # 데이터베이스 스키마
├── menubar/             # macOS 메뉴바 앱
├── web/                 # 웹 대시보드
├── homebrew/            # Homebrew Formula
├── docs/                # 문서
└── README.md
```

## 라이선스

MIT License
