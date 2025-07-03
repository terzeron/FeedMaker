#!/usr/bin/env python3

import sys
import tempfile
from pathlib import Path
from PIL import Image
sys.path.append(str(Path(__file__).parent))

from utils.image_downloader import ImageDownloader
from bin.crawler import Crawler
from bin.feed_maker_util import Env, Config


def create_test_image(width: int, height: int, format: str = "PNG") -> Path:
    """테스트용 이미지 생성"""
    temp_dir = Path(tempfile.mkdtemp())
    img_path = temp_dir / f"test_image_{width}x{height}.{format.lower()}"
    
    # 간단한 테스트 이미지 생성
    img = Image.new("RGB", (width, height), color="red")
    img.save(img_path, format)
    
    return img_path


def test_image_optimization():
    """이미지 최적화 테스트"""
    print("=== 이미지 최적화 테스트 시작 ===\n")
    
    test_cases = [
        {"width": 1200, "height": 800, "format": "PNG"},
        {"width": 600, "height": 900, "format": "PNG"},
        {"width": 1920, "height": 1080, "format": "JPEG"},
        {"width": 400, "height": 600, "format": "PNG"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"테스트 케이스 {i}: {case['width']}x{case['height']} {case['format']}")
        
        # 원본 이미지 생성
        original_path = create_test_image(case['width'], case['height'], case['format'])
        original_size = original_path.stat().st_size
        
        print(f"  원본 파일: {original_path.name}")
        print(f"  원본 크기: {original_size:,} bytes")
        
        # 최적화 적용
        optimized_path = ImageDownloader.convert_image_format(original_path)
        
        if optimized_path and optimized_path.exists():
            optimized_size = optimized_path.stat().st_size
            reduction = (1 - optimized_size / original_size) * 100
            
            with Image.open(optimized_path) as img:
                print(f"  최적화 파일: {optimized_path.name}")
                print(f"  최적화 크기: {optimized_size:,} bytes")
                print(f"  용량 감소: {reduction:.1f}%")
                print(f"  최종 해상도: {img.width}x{img.height}")
                print(f"  최종 포맷: {img.format}")
        else:
            print("  최적화 실패!")
        
        print()
        
        # 임시 파일 정리
        original_path.unlink(missing_ok=True)
        if optimized_path:
            optimized_path.unlink(missing_ok=True)
        original_path.parent.rmdir()


def test_webtoon_optimization():
    """웹툰 최적화 기능 테스트"""
    print("=== 웹툰 최적화 기능 테스트 ===\n")
    
    # 큰 이미지로 테스트
    large_img = Image.new("RGB", (1500, 2000), color="blue")
    small_img = Image.new("RGB", (600, 800), color="green")
    
    print("큰 이미지 테스트 (1500x2000):")
    optimized_large = ImageDownloader.optimize_for_webtoon(large_img, max_width=800)
    print(f"  최적화 후: {optimized_large.width}x{optimized_large.height}")
    
    print("\n작은 이미지 테스트 (600x800):")
    optimized_small = ImageDownloader.optimize_for_webtoon(small_img, max_width=800)
    print(f"  최적화 후: {optimized_small.width}x{optimized_small.height}")
    
    print()


if __name__ == "__main__":
    test_webtoon_optimization()
    test_image_optimization()
    print("모든 테스트 완료!")