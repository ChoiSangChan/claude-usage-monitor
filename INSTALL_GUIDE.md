# Claude Usage Monitor - 설치 가이드

> 비개발자도 따라할 수 있는 단계별 설치 안내서입니다.

---

## 사전 준비 (1회만 하면 됩니다)

### 1단계: Python 확인

터미널을 열고 아래를 복사 & 붙여넣기:

```
python3 --version
```

`Python 3.x.x` 이런 식으로 나오면 OK!
안 나오면 https://www.python.org/downloads/ 에서 Python을 설치해주세요.

### 2단계: xbar 설치 (macOS 메뉴바 앱)

터미널에서:

```
brew install --cask xbar
```

> brew가 없다면 먼저: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

---

## 설치하기

### 3단계: 프로젝트 다운로드

```
cd ~
git clone https://github.com/ChoiSangChan/claude-usage-monitor.git
cd claude-usage-monitor
```

### 4단계: 자동 설치

```
bash install.sh
```

이 명령 하나로 다음이 자동으로 됩니다:
- 데이터베이스 생성
- API 자동 추적 Hook 설정
- xbar 메뉴바 플러그인 설치

### 5단계: 터미널 재시작

```
source ~/.zshrc
```

또는 터미널 앱을 닫고 다시 열면 됩니다.

---

## 잘 설치되었는지 확인하기

```
python3 examples/test_api.py
```

아래처럼 나오면 성공입니다:
```
✅ 통과: 비용 계산
✅ 통과: DB 기록
✅ 통과: DB 조회
```

---

## 사용 방법

### 자동 모드 (설치만 하면 끝!)
Python에서 Anthropic/OpenAI API를 호출하면 **자동으로 사용량이 기록**됩니다.
별도로 뭔가 할 필요 없습니다.

### 메뉴바 확인
macOS 상단 메뉴바에 `💬 $0/100` 같은 아이콘이 표시됩니다.
- 클릭하면 상세 사용량을 볼 수 있습니다
- **10분마다 자동 갱신**됩니다

### 예산 변경
메뉴바에서 `설정 > 월 예산 변경` 클릭

---

## 문제 해결

### "xbar가 안 보여요"
1. xbar 앱을 실행해주세요 (Applications > xbar)
2. xbar 설정에서 Plugin Folder가 올바른지 확인

### "사용량이 안 잡혀요"
터미널에서 아래를 실행해 Hook이 제대로 설정되었는지 확인:
```
echo $PYTHONSTARTUP
```
경로가 나와야 합니다. 안 나오면 `bash install.sh`를 다시 실행해주세요.

### "데이터를 초기화하고 싶어요"
```
rm ~/.claude-usage-monitor/usage.db
bash install.sh
```
