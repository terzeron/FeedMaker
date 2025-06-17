#!/usr/bin/env python


import sys
import re
from pathlib import Path
from bin.feed_maker_util import URL, IO, Process, Env


def main() -> int:
    link = sys.argv[1]
    id_str = URL.get_short_md5_name(link)
    video_file = id_str + ".avi"
    img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / "thegoodmovie"
    img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/thegoodmovie"

    for line in IO.read_stdin_as_line_list():
        m = re.search(r"<video src='[^']*videoPath=(rtmp://[^&]*)[^']*'>", line)
        if m:
            movie_url = m.group(1)
            image_file_path = img_dir_path / f"{id_str}_0001.jpg"
            if not image_file_path.is_file():
                video_file_path = Path(video_file)
                if not video_file_path.is_file():
                    cmd = f"rtmpdump -q -r '{movie_url}' > {video_file}"
                    print(f"<!-- {cmd} -->")
                    result, error = Process.exec_cmd(cmd)
                    print(f"<!-- {result}, {error} -->")

                cmd = f"extract_images_from_video.sh '{video_file}' '{img_dir_path}/{id_str}_' > /dev/null 2>&1"
                print(f"<!-- {cmd} -->")
                result, error = Process.exec_cmd(cmd)
                print(f"<!-- {result}, {error}-->")

            for entry in img_dir_path.iterdir():
                if re.search(id_str + r"_\d+\.jpg", entry.name):
                    print(f"<img src='{img_url_prefix}/{entry.name}'/>\n")
            # unlink(video_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
