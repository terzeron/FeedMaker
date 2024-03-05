#!/usr/bin/env python


import sys
import filecmp
import logging.config
from pathlib import Path
from bin.feed_maker_util import Process

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def test_script(script: str, test_dir_path: Path, index: int):
    cmd = f"cat {test_dir_path}/input.{index}.txt | {script} > {test_dir_path}/result.{index}.temp"
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd)
    if not error:
        cmp_result = filecmp.cmp(f"{test_dir_path}/result.{index}.temp", f"{test_dir_path}/expected.output.{index}.txt")
        if not cmp_result:
            LOGGER.error(f"Error in diff '{test_dir_path}/expected.output.{index}.txt' '{test_dir_path}/result.{index}.temp'")
            return False, cmd
        return True, cmd
    LOGGER.error(error)
    return False, cmd


def main() -> int:
    fm_home = Path(__file__).parent.parent

    test_subjects = {
        "naver/one_second": [
            f"{fm_home}/utils/download_image.py -f ~/workspace/fma/naver/one_second 'https://comic.naver.com/webtoon/detail.nhn?titleId=711422&no=1'"
        ],
        "naver/windbreaker": [
            f"{fm_home}/utils/download_merge_split.py -f ~/workspace/fma/naver/windbreaker -m -c fuzzy 'https://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197'"
        ],
        "naver/naverpost.interbiz": [
            f"{fm_home}/bin/extractor.py -f ~/workspace/fma/naver/naverpost.interbiz 'http://m.post.naver.com/viewer/postView.nhn?volumeNo=14122118&memberNo=35786474'"
        ],
    }

    for (feed, scripts) in test_subjects.items():
        index = 0
        for script in scripts:
            index += 1
            LOGGER.info(feed)
            test_dir_path = Path(fm_home) / "test" / feed
            result, cmd = test_script(script, test_dir_path, index)
            if not result:
                LOGGER.error(f"Error in '{cmd}'\n")
                return -1
    LOGGER.info("Ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
