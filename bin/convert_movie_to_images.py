#!/usr/bin/env python


import sys
import os
import re
import feedmakerutil


def main():
    link = sys.argv[1]
    id = feedmakerutil.get_short_md5_name(link)
    video_file = id + ".avi"
    img_dir = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/thegoodmovie"
    img_url_prefix = "http://terzeron.net/xml/img/thegoodmovie"

    for line in feedmakerutil.read_stdin_as_line_list():
        m = re.search(r"<video src='[^']*videoPath=(rtmp://[^&]*)[^']*'>", line)
        if m:
            movie_url = m.group(1)
            image_file_name = "%s/%s_0001.jpg" % (img_dir, id)
            if not os.path.isfile(image_file_name): 
                if not os.path.isfile(video_file):
                    cmd = "/Users/terzeron/workspace/rtmpdump/rtmpdump -q -r '%s' > %s" % (movie_url, video_file) 
                    print("<!-- %s -->" % (cmd))
                    (result, error) = feedmakerutil.exec_cmd(cmd)
                    print("<!-- %s -->" % (result))
                
                cmd = "/Users/terzeron/bin/extract_images_from_video.sh '%s' '%s/%s_' > /dev/null 2>&1" % (video_file, img_dir, id)
                print("<!-- %s -->" % (cmd))
                (result, error) = feedmakerutil.exec_cmd(cmd)
                print("<!-- %s -->" % (result))

            for entry in os.scandir(img_dir):
                if re.search(r"%s_\d+\.jpg" % (id), entry.name):
                    print("<img src='%s/%s'/>\n" % (img_url_prefix, entry.name))
            #unlink(video_file)


if __name__ == "__main__":
    sys.exit(main())
