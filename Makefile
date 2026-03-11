# Claude Usage Monitor - Makefile
# 빌드, 테스트, 패키징을 위한 간편 명령어

.PHONY: install deps icon app dmg clean test run help

help: ## 도움말
	@echo ""
	@echo "  Claude Usage Monitor - Build Commands"
	@echo "  ──────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""

deps: ## 의존성 설치
	pip3 install -r requirements.txt

icon: ## 앱 아이콘 생성
	python3 app/resources/create_icon.py

app: deps icon ## .app 번들 빌드
	python3 setup.py py2app

dmg: ## DMG 파일 빌드 (전체 프로세스)
	./build_dmg.sh

run: ## 앱 직접 실행 (개발 모드)
	python3 app/claude_usage_monitor.py

test: ## 테스트 실행
	python3 examples/test_api.py

install: ## Hook & DB 설치
	./install.sh

clean: ## 빌드 산출물 정리
	rm -rf build/ dist/ dmg_staging/
	rm -f *.dmg
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
