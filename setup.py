"""
Claude Usage Monitor - py2app 빌드 설정
macOS .app 번들을 생성합니다.

사용법:
    python setup.py py2app
"""

import os
import sys
from pathlib import Path
from setuptools import setup

# py2app이 없으면 안내
try:
    import py2app  # noqa: F401
except ImportError:
    print("py2app이 필요합니다: pip install py2app")
    sys.exit(1)

APP = ["app/claude_usage_monitor.py"]
APP_NAME = "Claude Usage Monitor"
VERSION = "1.0.0"

# 아이콘 파일 경로
ICON_FILE = "app/resources/AppIcon.icns"
if not os.path.exists(ICON_FILE):
    # .icns가 없으면 .png 시도
    ICON_FILE = "app/resources/AppIcon.png"
    if not os.path.exists(ICON_FILE):
        ICON_FILE = None

DATA_FILES = [
    ("sql", ["sql/schema.sql"]),
    ("scripts", ["scripts/hook.py"]),
]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.claudeusagemonitor.app",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "LSUIElement": True,  # 메뉴바 전용 앱 (Dock에 표시 안 함)
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.15",
        "CFBundleDocumentTypes": [],
        "NSHumanReadableCopyright": "MIT License",
        "LSApplicationCategoryType": "public.app-category.developer-tools",
    },
    "includes": [
        "rumps",
        "sqlite3",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
    ],
    "resources": [
        "sql/schema.sql",
    ],
    "frameworks": [],
}

if ICON_FILE:
    OPTIONS["iconfile"] = ICON_FILE

setup(
    name=APP_NAME,
    version=VERSION,
    description="macOS 메뉴바에서 LLM API 사용량을 실시간으로 추적하는 모니터링 앱",
    author="Claude Usage Monitor",
    license="MIT",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    install_requires=["rumps>=0.4.0"],
)
