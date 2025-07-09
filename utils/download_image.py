#!/usr/bin/env python

import sys
import re
import getopt
import logging.config
from pathlib import Path
from utils.image_downloader import ImageDownloader
from bin.feed_maker_util import Config, IO, PathUtil, Env
from bin.crawler import Crawler


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    feed_dir_path = Path.cwd()
    quality = 75  # default quality

    optlist, args = getopt.getopt(sys.argv[1:], "f:q:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)
        elif o == "-q":
            quality = int(a)

    if not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url = args[0]
    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)

    config = Config(feed_dir_path)
    extraction_conf = config.get_extraction_configs()
    headers = {
        "User-Agent": extraction_conf.get("user_agent", ""),
        "Referer": page_url
    }
    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    line_list = IO.read_stdin_as_line_list()
    for line in line_list:
        # 이미지 태그 패턴
        img_pattern = r'<img[^>]*src=[\"\'](?P<img_url>[^\"\']+)[\"\'][^>]*/?>'
        
        # 이미지가 있는지 확인
        if re.search(img_pattern, line):
            # 이미지 태그를 순차적으로 교체
            def replace_img_tag(match: re.Match[str]) -> str:
                img_url = match.group("img_url")
                original_tag = match.group(0)
                
                try:
                    _, new_img_url = ImageDownloader.download_image(crawler, feed_img_dir_path, img_url, quality=quality)
                    if new_img_url:
                        # width 속성만 보존하고 나머지는 제거
                        width_match = re.search(r"width=['\"][^'\"]*['\"]", original_tag)
                        if width_match:
                            width_attr = width_match.group(0)
                            return f"<img src='{new_img_url}' {width_attr}/>"
                        else:
                            return f"<img src='{new_img_url}'/>"
                    else:
                        return "<img src='not_found.png' alt='not exist or size 0'/>"
                except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
                    LOGGER.error(f"이미지 다운로드 중 오류 발생: {e}")
                    return "<img src='not_found.png' alt='error occurred'/>"
            
            # 모든 이미지 태그를 교체
            new_line = re.sub(img_pattern, replace_img_tag, line)
            
            # 더 정확한 HTML 요소 분리
            # 중첩된 태그를 포함하여 완전한 HTML 요소를 찾는 패턴
            element_pattern = r'<([^/>]+)>([^<]*(?:<[^>]+/>[^<]*)*)</\1>|<[^>]+/>'
            
            current_pos = 0
            for match in re.finditer(element_pattern, new_line):
                # 이전 위치부터 현재 매치 시작까지의 텍스트
                if match.start() > current_pos:
                    text_before = new_line[current_pos:match.start()].strip()
                    if text_before:
                        print(text_before)
                
                # 완전한 HTML 요소 출력
                print(match.group(0))
                current_pos = match.end()
            
            # 마지막 남은 텍스트 출력
            if current_pos < len(new_line):
                text_after = new_line[current_pos:].strip()
                if text_after:
                    print(text_after)
        else:
            print(line, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
# Test comment
