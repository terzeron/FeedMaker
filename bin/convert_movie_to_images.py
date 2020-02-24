#!/usr/bin/env python


import sys
import os
import re
import feed_maker_util
from feed_maker_util import URL, IO, exec_cmd


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
            image_file_name = "%s/%s_0001.jpg" % (img_dir, id_str)
            if not os.path.isfile(image_file_name):
                if not os.path.isfile(video_file):
                    cmd = "rtmpdump -q -r '%s' > %s" % (movie_url, video_file)
                    print("<!-- %s -->" % cmd)
                    (result, error) = exec_cmd(cmd)
                    print("<!-- %s -->" % result)

                cmd = "extract_images_from_video.sh '%s' '%s/%s_' > /dev/null 2>&1" % (video_file, img_dir, id_str)
                print("<!-- %s -->" % cmd)
                (result, error) = exec_cmd(cmd)
                print("<!-- %s -->" % result)

            for entry in os.scandir(img_dir):
                if re.search(r"%s_\d+\.jpg" % id_str, entry.name):
                    print("<img src='%s/%s'/>\n" % (img_url_prefix, entry.name))
            # unlink(video_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
