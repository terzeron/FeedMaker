#!/usr/bin/env python

import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import requests


class AccessLog:
    loki_url = os.environ["FM_LOKI_URL"] + "/query_range"

    def loki_search(self, params) -> Tuple[List[str], Dict[str, Any]]:
        logs: List[str] = []
        stats: Dict[str, Any] = {}
        response = requests.get(self.loki_url, params=params, timeout=60)
        if response:
            json_data = response.json()
            if "status" in json_data and json_data["status"] == "success":
                if "data" in json_data and "result" in json_data["data"]:
                    if "stats" in json_data["data"]:
                        stats = json_data["data"]["stats"]

                    for result in json_data["data"]["result"]:
                        if "values" in result:
                            for _, log_item in result["values"]:
                                logs.append(log_item)
        return logs, stats


    def search(self, date_str: str) -> Tuple[List[Tuple[datetime, str]], List[Tuple[datetime, str]]]:
        duration_in_minutes = 60 * 24 * 1 # 1 days
        step_in_minutes = 60 * 6 # by 6 hours

        # 특정일 0시 0분 0초
        the_day = datetime.strptime(date_str, "%Y-%m-%d")

        accessed_feed_list: List[Tuple[datetime, str]] = []
        viewed_feed_list: List[Tuple[datetime, str]] = []
        for i in range(0, duration_in_minutes, step_in_minutes):
            start = (the_day + timedelta(minutes=i)).astimezone().isoformat()
            end = (the_day + timedelta(minutes=i + step_in_minutes)).astimezone().isoformat()
            params = {"query": '{namespace="feedmaker"}', "start": start, "end": end, "limit": 5000, "direction": "forward"}

            result, _ = self.loki_search(params)
            for log in result:
                m = re.search(r'\[(?P<time>[^\]]+)\] "GET (?P<uri>[^ ]+) HTTP[^"]+\" (?P<status>\d+)', log)
                if m:
                    if m.group("status") == "200" or m.group("status") == "304":
                        time = m.group("time")
                        dt = datetime.strptime(time, "%d/%b/%Y:%H:%M:%S %z")

                        uri = m.group("uri")
                        m = re.search(r'/xml/img/(?P<feed>[^/]+)/(?P<item>.+)', uri)
                        if m:
                            feed = m.group("feed")
                            #item = m.group("item")
                        m = re.search(r'/xml/(?P<feed>.+).xml', uri)
                        if m:
                            feed = m.group("feed")
                            accessed_feed_list.append((dt, feed))
                        m = re.search(r'/img/1x1\.jpg\?feed=(?P<feed>[^&]+)&item=(?P<item>.+)', uri)
                        if m:
                            feed = m.group("feed")
                            #item = m.group("item")
                            viewed_feed_list.append((dt, feed))

        return accessed_feed_list, viewed_feed_list


if __name__ == "__main__":
    access_log = AccessLog()
    start_ts = datetime.now()
    accessed_feed_list, viewed_feed_list = access_log.search("2024-02-26")
    accessed_feed_list, viewed_feed_list = access_log.search("2024-02-27")
    accessed_feed_list, viewed_feed_list = access_log.search("2024-02-28")
    import pprint
    pprint.pprint(len(accessed_feed_list))
    pprint.pprint(len(viewed_feed_list))
    end_ts = datetime.now()
    print("Elapsed time: ", end_ts - start_ts)
