#!/Usr/bin/env python3


import sys
import os
import re
import getopt
import subprocess
import feedmakerutil


def printUsage():
    print("Usage: %s\t[ -t <threshold> ] <output file>\n" % (sys.argv[0]))


def main():
    optlist, args = getopt.getopt(sys.argv[1:], "t:")
    for o, a in optlist:
        if o == "-t":
            threshold = float(a)
            print("%f" % threshold)

    if len(args) < 1:
        printUsage()
        return -1

    filePrefix = args[0]
    intermediateFile = filePrefix + ".intermediate"
    tempOutputFile = filePrefix + ".temp"
    outputFile = filePrefix + ".output"
    lineNumLinkMap = {}
    titleExistenceSet = set([])

    # split link and title into two separate files
    # and make line number & link mapping table
    with open(intermediateFile, 'w', encoding='utf-8') as outFile:
        lineNum = 1
        for line in feedmakerutil.readStdinAsLineList():
            if re.search(r"^\#", line):
                continue
            line = line.rstrip()
            (link, title) = line.split("\t")        
            lineNumLinkMap[lineNum] = link + "\t" + title
        
            cleanTitle = title.lower()
            cleanTitle = re.sub(r'[\s\!-\/\:-\@\[-\`]*', '', cleanTitle)
            if cleanTitle in titleExistenceSet:
                continue
            else:
                titleExistenceSet.add(cleanTitle)
            outFile.write("%s\n" % (title))
            lineNum += 1

    # hierarchical clustering
    clusterDir = os.environ["FEED_MAKER_HOME"] + "/../HierarchicalClustering"
    cmd = "%s/hcluster -t '%f' -s stop_words.txt '%s' '%s'" % (clusterDir, threshold, intermediateFile, tempOutputFile)
    print(cmd)
    result = feedmakerutil.execCmd(cmd)
    #print(result)

    # convert & extract temporary output file
    cmd = "awk -F'\\t' '$2 >= 3 { for (i = 3; i < NF; i += 2) { print $(i) FS $(i + 1) } }' '%s'" % (tempOutputFile)
    print(cmd)
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as p:
        with open(outputFile, 'w', encoding='utf-8') as outFile:
            for line in p.stdout:
                line = line.rstrip()
                (lineNum, title) = line.split("\t")
                outFile.write("%d\n" % (lineNumLinkMap[lineNum]))


if __name__ == "__main__":
    sys.exit(main())
