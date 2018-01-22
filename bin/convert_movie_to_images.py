#!/usr/bin/env python


import sys
import os
import re
import feedmakerutil


def main():
    link = sys.argv[1]
    id = feedmakerutil.get_short_md5_name(link)
    videoFile = id + ".avi"
    imgDir = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/thegoodmovie"
    imgUrlPrefix = "http://terzeron.net/xml/img/thegoodmovie"

    for line in feedmakerutil.read_stdin_as_line_list():
        m = re.search(r"<video src='[^']*videoPath=(rtmp://[^&]*)[^']*'>", line)
        if m:
            movieUrl = m.group(1)
            imageFileName = "%s/%s_0001.jpg" % (imgDir, id)
            if not os.path.isfile(imageFileName): 
                if not os.path.isfile(videoFile):
                    cmd = "/Users/terzeron/workspace/rtmpdump/rtmpdump -q -r '%s' > %s" % (movieUrl, videoFile) 
                    print("<!-- %s -->" % (cmd))
                    result = feedmakerutil.exec_cmd(cmd)
                    print("<!-- %s -->" % (result))
                
                cmd = "/Users/terzeron/bin/extract_images_from_video.sh '%s' '%s/%s_' > /dev/null 2>&1" % (videoFile, imgDir, id)
                print("<!-- %s -->" % (cmd))
                result = feedmakerutil.exec_cmd(cmd)
                print("<!-- %s -->" % (result))

            for entry in os.scandir(imgDir):
                if re.search(r"%s_\d+\.jpg" % (id), entry.name):
                    print("<img src='%s/%s'/>\n" % (imgUrlPrefix, entry.name))
            #unlink(videoFile)


if __name__ == "__main__":
    sys.exit(main())
