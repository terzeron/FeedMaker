const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const {
  createSuccess,
  createFailure,
  createGroupsResponse,
  createFeedsResponse,
  createProblemsResponse,
  createExecResultResponse,
  createSearchResponse,
  createSearchSiteResponse,
  createSiteNamesResponse,
  createSiteConfigResponse,
  createFeedInfoResponse,
  createCheckRunningResponse,
  createItemTitlesResponse,
  createNewNameResponse
} = require('./contracts');

// 환경변수 로드
dotenv.config({ path: path.join(__dirname, '../.env.development') });

const app = express();
const PORT = process.env.VUE_APP_API_PORT || 3000;

// CORS 설정
app.use(cors());
app.use(express.json());

// Mock 데이터
const mockData = {
  "groups": {
    "groups": [
      {
        "name": "webtoon",
        "num_feeds": 3,
        "status": true,
        "description": "웹툰 피드 그룹"
      },
      {
        "name": "news",
        "num_feeds": 2,
        "status": true,
        "description": "뉴스 피드 그룹"
      },
      {
        "name": "blog",
        "num_feeds": 1,
        "status": false,
        "description": "블로그 피드 그룹"
      },
      {
        "name": "tech",
        "num_feeds": 2,
        "status": true,
        "description": "기술 관련 피드 그룹"
      },
      {
        "name": "sports",
        "num_feeds": 1,
        "status": true,
        "description": "스포츠 피드 그룹"
      },
      {
        "name": "entertainment",
        "num_feeds": 2,
        "status": true,
        "description": "엔터테인먼트 피드 그룹"
      },
      {
        "name": "_disabled_group",
        "num_feeds": 0,
        "status": false,
        "description": "비활성화된 그룹"
      }
    ]
  },
  "feeds": {
    "webtoon": [
      {
        "name": "naver_webtoon",
        "title": "네이버 웹툰",
        "status": true,
        "description": "네이버 웹툰 피드"
      },
      {
        "name": "kakao_webtoon",
        "title": "카카오 웹툰",
        "status": true,
        "description": "카카오 웹툰 피드"
      },
      {
        "name": "lezhin_webtoon",
        "title": "레진 웹툰",
        "status": true,
        "description": "레진 웹툰 피드"
      },
      {
        "name": "_disabled_webtoon",
        "title": "비활성화 웹툰",
        "status": false,
        "description": "비활성화된 웹툰 피드"
      }
    ],
    "news": [
      {
        "name": "tech_news",
        "title": "기술 뉴스",
        "status": true,
        "description": "기술 뉴스 피드"
      },
      {
        "name": "sports_news",
        "title": "스포츠 뉴스",
        "status": true,
        "description": "스포츠 뉴스 피드"
      },
      {
        "name": "politics_news",
        "title": "정치 뉴스",
        "status": true,
        "description": "정치 뉴스 피드"
      }
    ],
    "blog": [
      {
        "name": "personal_blog",
        "title": "개인 블로그",
        "status": false,
        "description": "개인 블로그 피드"
      }
    ],
    "tech": [
      {
        "name": "github_trending",
        "title": "GitHub Trending",
        "status": true,
        "description": "GitHub 트렌딩 저장소"
      },
      {
        "name": "stackoverflow",
        "title": "Stack Overflow",
        "status": true,
        "description": "Stack Overflow 질문"
      },
      {
        "name": "dev_to",
        "title": "Dev.to",
        "status": true,
        "description": "Dev.to 개발자 블로그"
      }
    ],
    "sports": [
      {
        "name": "soccer_news",
        "title": "축구 뉴스",
        "status": true,
        "description": "축구 관련 뉴스"
      }
    ],
    "entertainment": [
      {
        "name": "movie_reviews",
        "title": "영화 리뷰",
        "status": true,
        "description": "최신 영화 리뷰"
      },
      {
        "name": "music_news",
        "title": "음악 뉴스",
        "status": true,
        "description": "음악 관련 뉴스"
      }
    ]
  },
  "problems": {
    "problems": [
      {
        "id": "091b2213-1c34-4200-b0a8-3c61eee11957",
        "type": "connection_error",
        "severity": "high",
        "message": "네이버 웹툰 서버 연결 실패",
        "feed_name": "naver_webtoon",
        "group_name": "webtoon",
        "timestamp": "2025-06-25T07:55:05.438207",
        "status": "open"
      },
      {
        "id": "cb1ca534-01a6-4912-ad0c-e4d77d51499e",
        "type": "parsing_error",
        "severity": "medium",
        "message": "카카오 웹툰 HTML 파싱 오류",
        "feed_name": "kakao_webtoon",
        "group_name": "webtoon",
        "timestamp": "2025-06-25T04:55:05.438218",
        "status": "resolved"
      },
      {
        "id": "a6660008-2193-4302-a412-c7cbea86c4e4",
        "type": "timeout_error",
        "severity": "low",
        "message": "GitHub API 응답 시간 초과",
        "feed_name": "github_trending",
        "group_name": "tech",
        "timestamp": "2025-06-25T08:55:05.438224",
        "status": "open"
      },
      {
        "id": "6915870c-ea8c-4b9b-8219-4c0bc4d93797",
        "type": "data_validation_error",
        "severity": "medium",
        "message": "스포츠 뉴스 데이터 형식 오류",
        "feed_name": "sports_news",
        "group_name": "news",
        "timestamp": "2025-06-25T06:55:05.438229",
        "status": "open"
      }
    ]
  },
  "exec_result": {
    "exec_result": [
      {
        "feed_name": "naver_webtoon",
        "group_name": "webtoon",
        "status": "success",
        "start_time": "2025-06-25T09:25:05.438230",
        "end_time": "2025-06-25T09:30:05.438232",
        "items_processed": 15,
        "items_success": 15,
        "items_failed": 0,
        "log": "Feed processing completed successfully"
      },
      {
        "feed_name": "kakao_webtoon",
        "group_name": "webtoon",
        "status": "partial_success",
        "start_time": "2025-06-25T09:35:05.438233",
        "end_time": "2025-06-25T09:40:05.438235",
        "items_processed": 8,
        "items_success": 7,
        "items_failed": 1,
        "log": "Feed processing completed with 1 error"
      },
      {
        "feed_name": "github_trending",
        "group_name": "tech",
        "status": "failed",
        "start_time": "2025-06-25T09:45:05.438236",
        "end_time": "2025-06-25T09:47:05.438238",
        "items_processed": 0,
        "items_success": 0,
        "items_failed": 0,
        "log": "API rate limit exceeded"
      }
    ]
  },
  "feed_info": {
    "webtoon/naver_webtoon": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/naver_webtoon"
          ],
          "feed_dir_path": "/feeds/webtoon/naver_webtoon",
          "feed_name": "naver_webtoon"
        },
        "rss": {
          "title": "네이버 웹툰",
          "description": "네이버 웹툰 최신 업데이트",
          "link": "https://terzeron.com/naver_webtoon.xml"
        },
        "extraction": {
          "list_url": "https://example.com/naver_webtoon",
          "list_url_parser": "naver_webtoon"
        }
      },
      "collection_info": {
        "num_collection_urls": 17,
        "collect_date": "2025-06-25T03:55:05.438243",
        "urllist_count": 16,
        "total_item_count": 7
      },
      "public_feed_info": {
        "num_items_in_result": 7,
        "size_of_result_file": 3430,
        "last_upload_date": "2025-06-25T09:34:05.438247"
      },
      "progress_info": {
        "current_index": 3,
        "total_item_count": 16,
        "unit_size_per_day": 3,
        "progress_ratio": 24.531196705540548,
        "feed_completion_due_date": "2025-06-28T09:55:05.438251"
      }
    },
    "webtoon/kakao_webtoon": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/kakao_webtoon"
          ],
          "feed_dir_path": "/feeds/webtoon/kakao_webtoon",
          "feed_name": "kakao_webtoon"
        },
        "rss": {
          "title": "카카오 웹툰",
          "description": "카카오 웹툰 최신 업데이트",
          "link": "https://terzeron.com/kakao_webtoon.xml"
        },
        "extraction": {
          "list_url": "https://example.com/kakao_webtoon",
          "list_url_parser": "kakao_webtoon"
        }
      },
      "collection_info": {
        "num_collection_urls": 5,
        "collect_date": "2025-06-24T09:55:05.438254",
        "urllist_count": 6,
        "total_item_count": 12
      },
      "public_feed_info": {
        "num_items_in_result": 12,
        "size_of_result_file": 2238,
        "last_upload_date": "2025-06-25T09:32:05.438257"
      },
      "progress_info": {
        "current_index": 7,
        "total_item_count": 20,
        "unit_size_per_day": 5,
        "progress_ratio": 89.51274195357001,
        "feed_completion_due_date": "2025-06-29T09:55:05.438259"
      }
    },
    "webtoon/lezhin_webtoon": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/lezhin_webtoon"
          ],
          "feed_dir_path": "/feeds/webtoon/lezhin_webtoon",
          "feed_name": "lezhin_webtoon"
        },
        "rss": {
          "title": "레진 웹툰",
          "description": "레진 웹툰 최신 업데이트",
          "link": "https://terzeron.com/lezhin_webtoon.xml"
        },
        "extraction": {
          "list_url": "https://example.com/lezhin_webtoon",
          "list_url_parser": "lezhin_webtoon"
        }
      },
      "collection_info": {
        "num_collection_urls": 5,
        "collect_date": "2025-06-25T00:55:05.438262",
        "urllist_count": 16,
        "total_item_count": 10
      },
      "public_feed_info": {
        "num_items_in_result": 7,
        "size_of_result_file": 3639,
        "last_upload_date": "2025-06-25T09:10:05.438265"
      },
      "progress_info": {
        "current_index": 10,
        "total_item_count": 16,
        "unit_size_per_day": 5,
        "progress_ratio": 48.424630734498386,
        "feed_completion_due_date": "2025-06-28T09:55:05.438267"
      }
    },
    "news/tech_news": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/tech_news"
          ],
          "feed_dir_path": "/feeds/news/tech_news",
          "feed_name": "tech_news"
        },
        "rss": {
          "title": "기술 뉴스",
          "description": "기술 뉴스 최신 업데이트",
          "link": "https://terzeron.com/tech_news.xml"
        },
        "extraction": {
          "list_url": "https://example.com/tech_news",
          "list_url_parser": "tech_news"
        }
      },
      "collection_info": {
        "num_collection_urls": 6,
        "collect_date": "2025-06-24T17:55:05.438270",
        "urllist_count": 9,
        "total_item_count": 9
      },
      "public_feed_info": {
        "num_items_in_result": 12,
        "size_of_result_file": 1944,
        "last_upload_date": "2025-06-25T09:12:05.438273"
      },
      "progress_info": {
        "current_index": 6,
        "total_item_count": 18,
        "unit_size_per_day": 2,
        "progress_ratio": 20.45951826306688,
        "feed_completion_due_date": "2025-06-26T09:55:05.438275"
      }
    },
    "news/sports_news": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/sports_news"
          ],
          "feed_dir_path": "/feeds/news/sports_news",
          "feed_name": "sports_news"
        },
        "rss": {
          "title": "스포츠 뉴스",
          "description": "스포츠 뉴스 최신 업데이트",
          "link": "https://terzeron.com/sports_news.xml"
        },
        "extraction": {
          "list_url": "https://example.com/sports_news",
          "list_url_parser": "sports_news"
        }
      },
      "collection_info": {
        "num_collection_urls": 15,
        "collect_date": "2025-06-24T18:55:05.438278",
        "urllist_count": 16,
        "total_item_count": 12
      },
      "public_feed_info": {
        "num_items_in_result": 17,
        "size_of_result_file": 1307,
        "last_upload_date": "2025-06-25T09:43:05.438281"
      },
      "progress_info": {
        "current_index": 8,
        "total_item_count": 14,
        "unit_size_per_day": 1,
        "progress_ratio": 16.485181586393004,
        "feed_completion_due_date": "2025-06-26T09:55:05.438283"
      }
    },
    "news/politics_news": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/politics_news"
          ],
          "feed_dir_path": "/feeds/news/politics_news",
          "feed_name": "politics_news"
        },
        "rss": {
          "title": "정치 뉴스",
          "description": "정치 뉴스 최신 업데이트",
          "link": "https://terzeron.com/politics_news.xml"
        },
        "extraction": {
          "list_url": "https://example.com/politics_news",
          "list_url_parser": "politics_news"
        }
      },
      "collection_info": {
        "num_collection_urls": 7,
        "collect_date": "2025-06-24T16:55:05.438285",
        "urllist_count": 10,
        "total_item_count": 11
      },
      "public_feed_info": {
        "num_items_in_result": 7,
        "size_of_result_file": 1361,
        "last_upload_date": "2025-06-25T09:43:05.438287"
      },
      "progress_info": {
        "current_index": 7,
        "total_item_count": 10,
        "unit_size_per_day": 5,
        "progress_ratio": 38.42035148130065,
        "feed_completion_due_date": "2025-06-27T09:55:05.438289"
      }
    },
    "tech/github_trending": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/github_trending"
          ],
          "feed_dir_path": "/feeds/tech/github_trending",
          "feed_name": "github_trending"
        },
        "rss": {
          "title": "GitHub Trending",
          "description": "GitHub Trending 최신 업데이트",
          "link": "https://terzeron.com/github_trending.xml"
        },
        "extraction": {
          "list_url": "https://example.com/github_trending",
          "list_url_parser": "github_trending"
        }
      },
      "collection_info": {
        "num_collection_urls": 20,
        "collect_date": "2025-06-24T13:55:05.438291",
        "urllist_count": 20,
        "total_item_count": 11
      },
      "public_feed_info": {
        "num_items_in_result": 9,
        "size_of_result_file": 3863,
        "last_upload_date": "2025-06-25T09:13:05.438293"
      },
      "progress_info": {
        "current_index": 3,
        "total_item_count": 19,
        "unit_size_per_day": 2,
        "progress_ratio": 18.953422794881625,
        "feed_completion_due_date": "2025-07-01T09:55:05.438294"
      }
    },
    "tech/stackoverflow": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/stackoverflow"
          ],
          "feed_dir_path": "/feeds/tech/stackoverflow",
          "feed_name": "stackoverflow"
        },
        "rss": {
          "title": "Stack Overflow",
          "description": "Stack Overflow 최신 업데이트",
          "link": "https://terzeron.com/stackoverflow.xml"
        },
        "extraction": {
          "list_url": "https://example.com/stackoverflow",
          "list_url_parser": "stackoverflow"
        }
      },
      "collection_info": {
        "num_collection_urls": 18,
        "collect_date": "2025-06-24T15:55:05.438296",
        "urllist_count": 9,
        "total_item_count": 6
      },
      "public_feed_info": {
        "num_items_in_result": 12,
        "size_of_result_file": 3288,
        "last_upload_date": "2025-06-25T09:24:05.438298"
      },
      "progress_info": {
        "current_index": 2,
        "total_item_count": 18,
        "unit_size_per_day": 2,
        "progress_ratio": 9.265991378622795,
        "feed_completion_due_date": "2025-07-01T09:55:05.438300"
      }
    },
    "tech/dev_to": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/dev_to"
          ],
          "feed_dir_path": "/feeds/tech/dev_to",
          "feed_name": "dev_to"
        },
        "rss": {
          "title": "Dev.to",
          "description": "Dev.to 최신 업데이트",
          "link": "https://terzeron.com/dev_to.xml"
        },
        "extraction": {
          "list_url": "https://example.com/dev_to",
          "list_url_parser": "dev_to"
        }
      },
      "collection_info": {
        "num_collection_urls": 16,
        "collect_date": "2025-06-24T15:55:05.438302",
        "urllist_count": 12,
        "total_item_count": 11
      },
      "public_feed_info": {
        "num_items_in_result": 15,
        "size_of_result_file": 2875,
        "last_upload_date": "2025-06-25T09:52:05.438303"
      },
      "progress_info": {
        "current_index": 7,
        "total_item_count": 16,
        "unit_size_per_day": 4,
        "progress_ratio": 93.63411229536946,
        "feed_completion_due_date": "2025-06-29T09:55:05.438305"
      }
    },
    "sports/soccer_news": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/soccer_news"
          ],
          "feed_dir_path": "/feeds/sports/soccer_news",
          "feed_name": "soccer_news"
        },
        "rss": {
          "title": "축구 뉴스",
          "description": "축구 뉴스 최신 업데이트",
          "link": "https://terzeron.com/soccer_news.xml"
        },
        "extraction": {
          "list_url": "https://example.com/soccer_news",
          "list_url_parser": "soccer_news"
        }
      },
      "collection_info": {
        "num_collection_urls": 11,
        "collect_date": "2025-06-24T15:55:05.438307",
        "urllist_count": 16,
        "total_item_count": 12
      },
      "public_feed_info": {
        "num_items_in_result": 11,
        "size_of_result_file": 3400,
        "last_upload_date": "2025-06-25T09:15:05.438309"
      },
      "progress_info": {
        "current_index": 8,
        "total_item_count": 11,
        "unit_size_per_day": 2,
        "progress_ratio": 87.39947648116136,
        "feed_completion_due_date": "2025-06-27T09:55:05.438311"
      }
    },
    "entertainment/movie_reviews": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/movie_reviews"
          ],
          "feed_dir_path": "/feeds/entertainment/movie_reviews",
          "feed_name": "movie_reviews"
        },
        "rss": {
          "title": "영화 리뷰",
          "description": "영화 리뷰 최신 업데이트",
          "link": "https://terzeron.com/movie_reviews.xml"
        },
        "extraction": {
          "list_url": "https://example.com/movie_reviews",
          "list_url_parser": "movie_reviews"
        }
      },
      "collection_info": {
        "num_collection_urls": 7,
        "collect_date": "2025-06-24T22:55:05.438312",
        "urllist_count": 6,
        "total_item_count": 19
      },
      "public_feed_info": {
        "num_items_in_result": 16,
        "size_of_result_file": 2226,
        "last_upload_date": "2025-06-25T09:31:05.438314"
      },
      "progress_info": {
        "current_index": 3,
        "total_item_count": 16,
        "unit_size_per_day": 1,
        "progress_ratio": 16.861826524324343,
        "feed_completion_due_date": "2025-06-26T09:55:05.438316"
      }
    },
    "entertainment/music_news": {
      "config": {
        "collection": {
          "list_url_list": [
            "https://example.com/music_news"
          ],
          "feed_dir_path": "/feeds/entertainment/music_news",
          "feed_name": "music_news"
        },
        "rss": {
          "title": "음악 뉴스",
          "description": "음악 뉴스 최신 업데이트",
          "link": "https://terzeron.com/music_news.xml"
        },
        "extraction": {
          "list_url": "https://example.com/music_news",
          "list_url_parser": "music_news"
        }
      },
      "collection_info": {
        "num_collection_urls": 20,
        "collect_date": "2025-06-24T13:55:05.438318",
        "urllist_count": 14,
        "total_item_count": 12
      },
      "public_feed_info": {
        "num_items_in_result": 16,
        "size_of_result_file": 3569,
        "last_upload_date": "2025-06-25T09:54:05.438320"
      },
      "progress_info": {
        "current_index": 10,
        "total_item_count": 13,
        "unit_size_per_day": 3,
        "progress_ratio": 58.91650066609942,
        "feed_completion_due_date": "2025-07-01T09:55:05.438322"
      }
    }
  }
};

const mockSearchSites = [
  'naver_webtoon',
  'kakao_webtoon',
  'lezhin_webtoon',
  'github_trending',
  'stackoverflow'
];

const defaultSiteConfig = {
  search_url_template: 'https://example.com/search?q={keyword}',
  parser: 'default',
  enabled: true
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function getGroups() {
  return mockData.groups.groups;
}

function getFeedsByGroup(groupName) {
  return mockData.feeds[groupName] || [];
}

function findFeed(groupName, feedName) {
  return (mockData.feeds[groupName] || []).find((feed) => feed.name === feedName);
}

function getFeedInfoKey(groupName, feedName) {
  return `${groupName}/${feedName}`;
}

function getMockFeedInfo(groupName, feedName) {
  return mockData.feed_info[getFeedInfoKey(groupName, feedName)] || null;
}

function normalizeFeedInfo(groupName, feedName) {
  const info = getMockFeedInfo(groupName, feedName);
  const feed = findFeed(groupName, feedName);

  if (!info && !feed) {
    return null;
  }

  const config = clone(info?.config || {
    collection: {
      list_url_list: [`https://example.com/${feedName}`]
    },
    extraction: {},
    rss: {
      title: feed?.title || feedName,
      description: feed?.description || `${feedName} feed`,
      link: `https://example.com/${feedName}.xml`
    }
  });

  return {
    feed_name: feedName,
    feed_title: config.rss?.title || feed?.title || feedName,
    group_name: groupName,
    config,
    config_modify_date: new Date().toISOString(),
    collection_info: {
      collect_date: info?.collection_info?.collect_date || null,
      total_item_count: info?.collection_info?.total_item_count || 0
    },
    public_feed_info: {
      public_feed_file_path: `/xml/${feedName}.xml`,
      file_size:
        info?.public_feed_info?.file_size ??
        info?.public_feed_info?.size_of_result_file ??
        0,
      num_items:
        info?.public_feed_info?.num_items ??
        info?.public_feed_info?.num_items_in_result ??
        0,
      upload_date:
        info?.public_feed_info?.upload_date ??
        info?.public_feed_info?.last_upload_date ??
        null
    },
    progress_info: {
      current_index: info?.progress_info?.current_index || 0,
      total_item_count: info?.progress_info?.total_item_count || 0,
      unit_size_per_day: info?.progress_info?.unit_size_per_day || 0,
      progress_ratio: info?.progress_info?.progress_ratio || 0,
      due_date:
        info?.progress_info?.due_date ??
        info?.progress_info?.feed_completion_due_date ??
        null
    }
  };
}

function getSiteConfig(groupName) {
  const group = mockData.groups.groups.find((item) => item.name === groupName);
  return {
    group_name: groupName,
    display_name: group?.description || groupName,
    ...defaultSiteConfig
  };
}

function toggleLeadingUnderscore(name) {
  return String(name || '').startsWith('_') ? String(name).slice(1) : `_${name}`;
}

function renameGroup(oldName, newName) {
  if (oldName === newName) {
    return;
  }

  const group = mockData.groups.groups.find((item) => item.name === oldName);
  if (group) {
    group.name = newName;
  }

  if (mockData.feeds[oldName]) {
    mockData.feeds[newName] = mockData.feeds[oldName];
    delete mockData.feeds[oldName];
  }

  Object.keys(mockData.feed_info).forEach((key) => {
    if (key.startsWith(`${oldName}/`)) {
      const newKey = `${newName}/${key.slice(oldName.length + 1)}`;
      mockData.feed_info[newKey] = mockData.feed_info[key];
      delete mockData.feed_info[key];
    }
  });
}

function renameFeed(groupName, oldFeedName, newFeedName) {
  if (oldFeedName === newFeedName) {
    return;
  }

  const feeds = mockData.feeds[groupName] || [];
  const feed = feeds.find((item) => item.name === oldFeedName);
  if (feed) {
    feed.name = newFeedName;
  }

  const oldKey = getFeedInfoKey(groupName, oldFeedName);
  const newKey = getFeedInfoKey(groupName, newFeedName);
  if (mockData.feed_info[oldKey]) {
    mockData.feed_info[newKey] = mockData.feed_info[oldKey];
    delete mockData.feed_info[oldKey];
  }
}

function buildSearchResults(keyword) {
  const normalizedKeyword = String(keyword || '').toLowerCase();

  return Object.entries(mockData.feeds)
    .flatMap(([groupName, feeds]) =>
      feeds
        .filter((feed) => {
          if (!normalizedKeyword) {
            return true;
          }
          return [groupName, feed.name, feed.title, feed.description]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(normalizedKeyword));
        })
        .map((feed) => ({
          group_name: groupName,
          feed_name: feed.name,
          feed_title: feed.title,
          description: feed.description,
        }))
    )
    .slice(0, 10);
}

function buildProblemResult(problemType) {
  const feedInfos = Object.entries(mockData.feed_info).map(([key, info]) => {
    const [groupName, feedName] = key.split('/');
    const normalized = normalizeFeedInfo(groupName, feedName);
    return {
      group_name: groupName,
      feed_name: feedName,
      feed_title: normalized?.feed_title || feedName,
      info: normalized
    };
  });

  switch (problemType) {
    case 'status_info':
      return feedInfos.map(({ group_name, feed_name, feed_title, info }) => ({
        group_name,
        feed_name,
        feed_title,
        http_request: true,
        public_html: true,
        feedmaker: true,
        update_date: info?.collection_info?.collect_date || null,
        upload_date: info?.public_feed_info?.upload_date || null,
        access_date: info?.public_feed_info?.upload_date || null,
        view_date: info?.public_feed_info?.upload_date || null
      }));
    case 'progress_info':
      return feedInfos.map(({ group_name, feed_name, feed_title, info }) => ({
        group_name,
        feed_name,
        feed_title,
        ...(info?.progress_info || {})
      }));
    case 'public_feed_info':
      return feedInfos.map(({ group_name, feed_name, feed_title, info }) => ({
        group_name,
        feed_name,
        feed_title,
        file_size: info?.public_feed_info?.file_size || 0,
        num_items: info?.public_feed_info?.num_items || 0,
        upload_date: info?.public_feed_info?.upload_date || null
      }));
    case 'html_info':
      return {
        html_file_size_map: feedInfos.slice(0, 2).map(({ group_name, feed_name, feed_title }) => ({
          feed_title,
          feed_dir_path: `${group_name}/${feed_name}`,
          file_path: `${group_name}/${feed_name}/html/sample.html`,
          file_size: 4096
        })),
        html_file_with_many_image_tag_map: [],
        html_file_without_image_tag_map: [],
        html_file_image_not_found_map: []
      };
    case 'element_info':
      return [
        { element_name: 'title', count: 12 },
        { element_name: 'content', count: 9 }
      ];
    case 'list_url_info':
      return feedInfos.map(({ group_name, feed_name, feed_title, info }) => ({
        group_name,
        feed_name,
        feed_title,
        list_url_count: info?.config?.collection?.list_url_list?.length || 0
      }));
    default:
      return [];
  }
}

function buildExecResultMarkdown() {
  const items = mockData.exec_result.exec_result || [];
  if (items.length === 0) {
    return '### No execution result available';
  }

  return items
    .map((item) =>
      [
        `### ${item.group_name}/${item.feed_name}`,
        `- status: ${item.status}`,
        `- processed: ${item.items_processed}`,
        `- success: ${item.items_success}`,
        `- failed: ${item.items_failed}`,
        `- log: ${item.log}`
      ].join('\n')
    )
    .join('\n\n');
}

function buildSearchSiteHtml(siteName, keyword) {
  return [
    `<h3>${siteName}</h3>`,
    `<p>Search keyword: ${keyword}</p>`,
    `<ul>`,
    `<li>${siteName} result 1</li>`,
    `<li>${siteName} result 2</li>`,
    `</ul>`
  ].join('');
}

// 로깅 미들웨어
app.use((req, res, next) => {
  console.log(`[Mock API] ${req.method} ${req.url}`);
  next();
});

// OpenAPI 스펙에 따른 라우팅 처리

app.post('/auth/login', (req, res) => {
    res.json(createSuccess({ message: '로그인되었습니다.' }));
});

app.post('/auth/logout', (req, res) => {
    res.json(createSuccess({ message: '로그아웃되었습니다.' }));
});

app.get('/auth/me', (req, res) => {
    res.json({
        is_authenticated: true,
        email: 'mock@example.com',
        name: 'Mock Admin',
        profile_picture_url: null
    });
});

// Get Exec Result
app.get('/exec_result', (req, res) => {
    res.json(createExecResultResponse(buildExecResultMarkdown()));
});
// Get Problems
app.get('/problems/:problem_type', (req, res) => {
    const { problem_type } = req.params;
    res.json(createProblemsResponse(buildProblemResult(problem_type)));
});
// Search
app.get('/search/:keyword', (req, res) => {
    const { keyword } = req.params;
    res.json(createSearchResponse(buildSearchResults(keyword)));
});
// Search Site
app.get('/search_site/:keyword', (req, res) => {
    const { keyword } = req.params;
    res.json(createSearchSiteResponse(buildSearchSiteHtml('default', keyword)));
});

app.get('/search_sites', (req, res) => {
    res.json(createSiteNamesResponse(mockSearchSites));
});

app.get('/search_sites/:site_name/:keyword', (req, res) => {
    const { site_name, keyword } = req.params;
    res.json(createSearchSiteResponse(buildSearchSiteHtml(site_name, keyword)));
});
// Remove Public Feed
app.delete('/public_feeds/:feed', (req, res) => {
    res.json(createSuccess({ message: 'Public feed removed' }));
});

app.get('/public_feeds/:feed/item_titles', (req, res) => {
    const { feed } = req.params;
    const infoEntry = Object.values(mockData.feed_info).find((item) => item?.config?.collection?.feed_name === feed);
    const title = infoEntry?.config?.rss?.title || feed;
    res.json(createItemTitlesResponse([`${title} item 1`, `${title} item 2`, `${title} item 3`]));
});
// Get Site Config
app.get('/groups/:group/site_config', (req, res) => {
    const { group } = req.params;
    res.json(createSiteConfigResponse(getSiteConfig(group)));
});
// Save Site Config
app.put('/groups/:group/site_config', (req, res) => {
    res.json(createSuccess({ message: 'Site config updated' }));
});
// Toggle Group
app.put('/groups/:group/toggle', (req, res) => {
    const { group } = req.params;
    const groupIndex = mockData.groups.groups.findIndex((g) => g.name === group);
    if (groupIndex !== -1) {
        const newName = toggleLeadingUnderscore(group);
        renameGroup(group, newName);
        res.json(createNewNameResponse(newName));
    } else {
        res.status(404).json(createFailure('Group not found'));
    }
});
// Remove Html File
app.delete('/groups/:group/feeds/:feed/htmls/:file', (req, res) => {
    res.json(createSuccess({ message: 'HTML file removed' }));
});
// Remove Html
app.delete('/groups/:group/feeds/:feed/htmls', (req, res) => {
    res.json(createSuccess({ message: 'HTML file removed' }));
});
// Run
app.post('/groups/:group/feeds/:feed/run', (req, res) => {
    res.json(createSuccess());
});
// Toggle Feed
app.put('/groups/:group/feeds/:feed/toggle', (req, res) => {
    const { group, feed } = req.params;
    const feedItem = findFeed(group, feed);
    if (feedItem) {
        const newName = toggleLeadingUnderscore(feed);
        renameFeed(group, feed, newName);
        res.json(createNewNameResponse(newName));
    } else {
        res.status(404).json(createFailure('Feed not found'));
    }
});
// Remove List
app.delete('/groups/:group/feeds/:feed/list', (req, res) => {
    res.json(createSuccess({ message: 'List removed' }));
});
// Check Running
app.get('/groups/:group/feeds/:feed/check_running', (req, res) => {
    res.json(createCheckRunningResponse(false));
});
// Get Feed Info
app.get('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    const feedInfo = normalizeFeedInfo(group, feed);
    if (!feedInfo) {
        res.status(404).json(createFailure('feed info not found'));
        return;
    }
    res.json(createFeedInfoResponse(feedInfo));
});
// Post Feed Info
app.post('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    const configuration = req.body?.configuration;
    if (!configuration) {
        res.json(createFailure("invalid configuration format (no 'configuration')"));
        return;
    }

    if (!findFeed(group, feed)) {
        if (!mockData.feeds[group]) {
            mockData.feeds[group] = [];
        }
        mockData.feeds[group].push({
            name: feed,
            title: configuration?.rss?.title || feed,
            status: true,
            description: configuration?.rss?.description || `${feed} feed`
        });
    }

    mockData.feed_info[getFeedInfoKey(group, feed)] = {
        config: clone(configuration),
        collection_info: {
            collect_date: new Date().toISOString(),
            total_item_count: 0
        },
        public_feed_info: {
            file_size: 0,
            num_items: 0,
            upload_date: null
        },
        progress_info: {
            current_index: 0,
            total_item_count: 0,
            unit_size_per_day: 0,
            progress_ratio: 0,
            due_date: null
        }
    };

    res.json(createSuccess());
});
// Delete Feed Info
app.delete('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    const feedIndex = mockData.feeds[group]?.findIndex((f) => f.name === feed);
    if (feedIndex !== -1) {
        mockData.feeds[group].splice(feedIndex, 1);
        delete mockData.feed_info[getFeedInfoKey(group, feed)];
        res.json(createSuccess());
    } else {
        res.status(404).json(createFailure('Feed not found'));
    }
});
// Get Feeds By Group
app.get('/groups/:group/feeds', (req, res) => {
    const { group } = req.params;
    res.json(createFeedsResponse(getFeedsByGroup(group)));
});
// Remove Group
app.delete('/groups/:group', (req, res) => {
    const { group } = req.params;
    
    const groupIndex = mockData.groups.groups.findIndex((g) => g.name === group);
    if (groupIndex !== -1) {
        mockData.groups.groups.splice(groupIndex, 1);
        delete mockData.feeds[group];
        Object.keys(mockData.feed_info).forEach((key) => {
            if (key.startsWith(`${group}/`)) {
                delete mockData.feed_info[key];
            }
        });
        res.json(createSuccess({ feeds: true }));
    } else {
        res.status(404).json(createFailure('Group not found'));
    }
});
// Get Groups
app.get('/groups', (req, res) => {
    res.json(createGroupsResponse(getGroups()));
});

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json(createFailure(`Endpoint ${req.method} ${req.originalUrl} not found`));
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Mock API Server running on http://localhost:${PORT}`);
  console.log(`📁 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 API URL: ${process.env.VUE_APP_API_URL || `http://localhost:${PORT}`}`);
  console.log(`📊 Mock data loaded: ${Object.keys(mockData).length} categories`);
});
