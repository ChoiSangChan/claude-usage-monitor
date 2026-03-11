#!/usr/bin/env python3
"""
Claude Usage Monitor - 앱 아이콘 생성기
Pillow를 사용하여 .icns 파일을 생성합니다.
Pillow가 없으면 기본 아이콘 없이 빌드됩니다.
"""

import os
import struct
import sys
from pathlib import Path


def create_simple_icon_png(size=512):
    """Pillow 없이 간단한 PNG 아이콘 생성 (단색 배경 + 텍스트 없음)."""
    # 최소한의 PNG를 직접 생성 (Pillow 의존성 제거)
    # 보라색 그라데이션 원형 아이콘
    import zlib

    width = height = size
    raw_data = bytearray()

    cx, cy = size // 2, size // 2
    radius = size // 2 - 4

    for y in range(height):
        raw_data.append(0)  # PNG filter: None
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= radius:
                # 그라데이션: 상단 보라(#7C3AED) → 하단 파랑(#3B82F6)
                t = y / height
                r = int(124 * (1 - t) + 59 * t)
                g = int(58 * (1 - t) + 130 * t)
                b = int(237 * (1 - t) + 246 * t)

                # 엣지 안티앨리어싱
                edge_dist = radius - dist
                if edge_dist < 2:
                    alpha = int(255 * edge_dist / 2)
                else:
                    alpha = 255

                raw_data.extend([r, g, b, alpha])
            else:
                raw_data.extend([0, 0, 0, 0])

    # PNG 생성
    def png_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png += png_chunk(b"IHDR", ihdr_data)
    # IDAT
    compressed = zlib.compress(bytes(raw_data), 9)
    png += png_chunk(b"IDAT", compressed)
    # IEND
    png += png_chunk(b"IEND", b"")

    return png


def create_icns(output_path):
    """iconutil을 사용하여 .icns 파일 생성 (macOS 전용)."""
    import subprocess
    import tempfile

    iconset_dir = Path(tempfile.mkdtemp()) / "AppIcon.iconset"
    iconset_dir.mkdir(parents=True)

    # 필요한 크기들
    sizes = [16, 32, 64, 128, 256, 512]

    for size in sizes:
        png_data = create_simple_icon_png(size)

        # 1x
        with open(iconset_dir / f"icon_{size}x{size}.png", "wb") as f:
            f.write(png_data)

        # 2x (retina)
        if size <= 256:
            png_data_2x = create_simple_icon_png(size * 2)
            with open(iconset_dir / f"icon_{size}x{size}@2x.png", "wb") as f:
                f.write(png_data_2x)

    # iconutil로 .icns 생성 (macOS에서만 동작)
    try:
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)],
            check=True,
            capture_output=True,
        )
        print(f"  아이콘 생성 완료: {output_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # macOS가 아니거나 iconutil이 없는 경우
        # 512px PNG를 대신 저장
        png_path = output_path.with_suffix(".png")
        png_data = create_simple_icon_png(512)
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"  PNG 아이콘 생성 (iconutil 미사용): {png_path}")
        return False


if __name__ == "__main__":
    resources_dir = Path(__file__).parent
    output = resources_dir / "AppIcon.icns"
    create_icns(output)
