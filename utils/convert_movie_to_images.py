#!/usr/bin/env python


import sys
import os
import re
from bin.feed_maker_util import URL, IO, Process


def main() -> int:
    link = sys.argv[1]
    id_str = URL.get_short_md5_name(link)
    video_file = id_str + ".avi"
    img_dir = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/thegoodmovie"
    img_url_prefix = "https://terzeron.com/xml/img/thegoodmovie"

    for line in IO.read_stdin_as_line_list():
        m = re.search(r"<video src='[^']*videoPath=(rtmp://[^&]*)[^']*'>", line)
        if m:
            movie_url = m.group(1)
            image_file_name = f"{img_dir}/{id_str}_0001.jpg"
            if not os.path.isfile(image_file_name):
                if not os.path.isfile(video_file):
                    cmd = f"rtmpdump -q -r '{movie_url}' > {video_file}"
                    print(f"<!-- {cmd} -->")
                    result, error = Process.exec_cmd(cmd)
                    print(f"<!-- {result}, {error} -->")

                cmd = f"extract_images_from_video.sh '{video_file}' '{img_dir}/{id_str}_' > /dev/null 2>&1"
                print(f"<!-- {cmd} -->")
                result, error = Process.exec_cmd(cmd)
                print(f"<!-- {result}, {error}-->")

            for entry in os.scandir(img_dir):
                if re.search(id_str + r"_\d+\.jpg", entry.name):
                    print(f"<img src='{img_url_prefix}/{entry.name}'/>\n")
            # unlink(video_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
