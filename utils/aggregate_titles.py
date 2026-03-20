#!/usr/bin/env python


import sys
import re
import getopt
import logging.config
from pathlib import Path
from bin.feed_maker_util import IO, Process


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def print_usage() -> None:
    print(f"_usage: {sys.argv[0]}\t[ -t <threshold> ] <output file>\n")


def _extract_clustered_lines(temp_output_file: Path) -> list[tuple[str, str]]:
    """TSV에서 2번째 필드 >= 3인 행의 (line_num, title) 쌍을 추출"""
    results: list[tuple[str, str]] = []
    if not temp_output_file.exists():
        return results
    with open(temp_output_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            count = int(fields[1])
            if count < 3:
                continue
            # fields[2:]부터 (line_num, title) 쌍
            for i in range(2, len(fields) - 1, 2):
                results.append((fields[i], fields[i + 1]))
    return results


def main() -> int:
    threshold: float = 0.0
    optlist, args = getopt.getopt(sys.argv[1:], "f:t:")
    for o, a in optlist:
        if o == "-t":
            threshold = float(a)
            print(threshold)

    if len(args) < 1:
        print_usage()
        return -1

    file_prefix = args[0]
    intermediate_file = file_prefix + ".intermediate"
    temp_output_file = file_prefix + ".temp"
    output_file = file_prefix + ".output"
    line_num_link_map: dict[int, str] = {}
    title_existence_set: set[str] = set()

    # split link and title into two separate files
    # and make line number & link mapping table
    with open(intermediate_file, "w", encoding="utf-8") as out_file:
        line_num = 1
        for line in IO.read_stdin_as_line_list():
            if re.search(r"^#", line):
                continue
            line = line.rstrip()
            link, title, _ = line.split("\t")
            clean_title = title.lower()
            clean_title = re.sub(r"[\s!-/:-@\[-`]*", "", clean_title)
            if clean_title not in title_existence_set:
                title_existence_set.add(clean_title)
                line_num_link_map[line_num] = link + "\t" + title
                out_file.write(f"{title}\n")
                line_num += 1

    # hierarchical clustering
    cluster_dir = Path(__file__).parent.parent / "HierarchicalClustering"
    cmd = f"{cluster_dir}/hcluster -t '{threshold}' -s stop_words.txt '{intermediate_file}' '{temp_output_file}'"
    LOGGER.debug(cmd)
    result, error = Process.exec_cmd(cmd)
    LOGGER.debug(result, error)

    # convert & extract temporary output file
    pairs = _extract_clustered_lines(Path(temp_output_file))
    with open(output_file, "w", encoding="utf-8") as out_file:
        for line_num_str, _ in pairs:
            line_num = int(line_num_str)
            out_file.write(f"{line_num_link_map[line_num]}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
