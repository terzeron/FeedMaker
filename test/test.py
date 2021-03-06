#!/usr/bin/env python


import sys
import os
import filecmp
import logging
import logging.config
import feed_maker_util


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def test_script(script, work_dir, test_dir, index):
    os.chdir(work_dir)
    cmd = "cat %s/input.%d.txt | %s > %s/result.%d.temp" % (test_dir, index, script, test_dir, index)
    LOGGER.debug(cmd)
    (result, error) = feed_maker_util.exec_cmd(cmd)
    if not error:
        os.chdir(test_dir)
        cmp_result = filecmp.cmp("result.%d.temp" % index, "expected.output.%d.txt" % index)
        if not cmp_result:
            LOGGER.error("Error in diff '%s/expected.output.%d.txt' '%s/result.%d.temp'" % (test_dir, index, test_dir, index))
            return (False, cmd)
        else:
            return (True, cmd)
    LOGGER.error(error)
    return (False, cmd)


def main():
    fm_cwd = os.getenv("FEED_MAKER_WORK_DIR")
    fm_home = os.getenv("FEED_MAKER_HOME_DIR")

    test_subjects = {
        "naver/bingtanghuru": [fm_home + "/bin/download_image.py 'http://comic.naver.com/webtoon/detail.nhn?titleId=695321&no=39'"],
        "naver/windbreaker": [fm_home + "/bin/download_merge_split.py -m -c fuzzy 'http://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197'"],
        "naver/naverpost.businessinsight": [fm_home + "/bin/extract.py 'http://m.post.naver.com/viewer/postView.nhn?volumeNo=14122118&memberNo=35786474'"],
        #"kakao/higher_than_my_shoulders": [fm_home + "/bin/post_process_only_for_images.py"],
        # "bookdb/to_lover_of_my_lover": [fm_home + "/bin/remove_non_breaking_space.py"],
    }

    for (feed, scripts) in test_subjects.items():
        index = 0
        for script in scripts:
            index += 1
            LOGGER.info("%s", feed)
            work_dir = fm_cwd + "/" + feed
            test_dir = fm_home + "/test/" + feed
            result, cmd = test_script(script, work_dir, test_dir, index)
            if not result:
                LOGGER.error("Error in '%s'\n", cmd)
                return -1
    LOGGER.info("Ok")


if __name__ == "__main__":
    sys.exit(main())
