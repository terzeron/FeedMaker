const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

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

// 로깅 미들웨어
app.use((req, res, next) => {
  console.log(`[Mock API] ${req.method} ${req.url}`);
  next();
});

// OpenAPI 스펙에 따른 라우팅 처리

// Get Exec Result
app.get('/exec_result', (req, res) => {
    const {  } = req.params;
    res.json({ status: 'success', message: 'Get Exec Result - Mock response' })
});
// Get Problems
app.get('/problems/:problem_type', (req, res) => {
    const { problem_type } = req.params;
    res.json(mockData.problems)
});
// Search
app.get('/search/:keyword', (req, res) => {
    const { keyword } = req.params;
    
    const query = req.query.q || '';
    const results = [];
    
    // 그룹에서 검색
    mockData.groups.groups.forEach(group => {
        if (group.name.toLowerCase().includes(query.toLowerCase()) || 
            group.description.toLowerCase().includes(query.toLowerCase())) {
            results.push({ type: 'group', data: group });
        }
    });
    
    // 피드에서 검색
    Object.entries(mockData.feeds).forEach(([groupName, feeds]) => {
        feeds.forEach(feed => {
            if (feed.name.toLowerCase().includes(query.toLowerCase()) || 
                feed.title.toLowerCase().includes(query.toLowerCase()) ||
                feed.description.toLowerCase().includes(query.toLowerCase())) {
                results.push({ type: 'feed', data: feed, group: groupName });
            }
        });
    });
    
    res.json({ results: results.slice(0, 10) });
});
// Search Site
app.get('/search_site/:keyword', (req, res) => {
    const { keyword } = req.params;
    
    const query = req.query.q || '';
    const results = [];
    
    // 그룹에서 검색
    mockData.groups.groups.forEach(group => {
        if (group.name.toLowerCase().includes(query.toLowerCase()) || 
            group.description.toLowerCase().includes(query.toLowerCase())) {
            results.push({ type: 'group', data: group });
        }
    });
    
    // 피드에서 검색
    Object.entries(mockData.feeds).forEach(([groupName, feeds]) => {
        feeds.forEach(feed => {
            if (feed.name.toLowerCase().includes(query.toLowerCase()) || 
                feed.title.toLowerCase().includes(query.toLowerCase()) ||
                feed.description.toLowerCase().includes(query.toLowerCase())) {
                results.push({ type: 'feed', data: feed, group: groupName });
            }
        });
    });
    
    res.json({ results: results.slice(0, 10) });
});
// Remove Public Feed
app.delete('/public_feeds/:feed', (req, res) => {
    const { feed } = req.params;
    
    res.json({ status: 'success', message: 'Public feed removed' });
});
// Get Site Config
app.get('/groups/:group/site_config', (req, res) => {
    const { group } = req.params;
    res.json(mockData.groups)
});
// Save Site Config
app.put('/groups/:group/site_config', (req, res) => {
    const { group } = req.params;
    
    res.json({ status: 'success', message: 'Site config updated' });
});
// Toggle Group
app.put('/groups/:group/toggle', (req, res) => {
    const { group } = req.params;
    
    const groupIndex = mockData.groups.groups.findIndex(g => g.name === req.params.group);
    if (groupIndex !== -1) {
        mockData.groups.groups[groupIndex].status = !mockData.groups.groups[groupIndex].status;
        res.json({ status: 'success', group: mockData.groups.groups[groupIndex] });
    } else {
        res.status(404).json({ status: 'error', message: 'Group not found' });
    }
});
// Remove Html File
app.delete('/groups/:group/feeds/:feed/htmls/:file', (req, res) => {
    const { group, feed, file } = req.params;
    
    res.json({ status: 'success', message: 'HTML file removed' });
});
// Remove Html
app.delete('/groups/:group/feeds/:feed/htmls', (req, res) => {
    const { group, feed } = req.params;
    
    res.json({ status: 'success', message: 'HTML file removed' });
});
// Run
app.post('/groups/:group/feeds/:feed/run', (req, res) => {
    const { group, feed } = req.params;
    
    const newGroup = req.body;
    newGroup.name = newGroup.name || 'new_group_' + Date.now();
    newGroup.num_feeds = 0;
    newGroup.status = true;
    newGroup.description = newGroup.description || '새로운 그룹';
    
    mockData.groups.groups.push(newGroup);
    res.json({ status: 'success', group: newGroup });
});
// Toggle Feed
app.put('/groups/:group/feeds/:feed/toggle', (req, res) => {
    const { group, feed } = req.params;
    
    const groupIndex = mockData.groups.groups.findIndex(g => g.name === req.params.group);
    if (groupIndex !== -1) {
        mockData.groups.groups[groupIndex].status = !mockData.groups.groups[groupIndex].status;
        res.json({ status: 'success', group: mockData.groups.groups[groupIndex] });
    } else {
        res.status(404).json({ status: 'error', message: 'Group not found' });
    }
});
// Remove List
app.delete('/groups/:group/feeds/:feed/list', (req, res) => {
    const { group, feed } = req.params;
    
    res.json({ status: 'success', message: 'List removed' });
});
// Check Running
app.get('/groups/:group/feeds/:feed/check_running', (req, res) => {
    const { group, feed } = req.params;
    res.json({ feeds: mockData.feeds[group] || [] })
});
// Get Feed Info
app.get('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    res.json({ feeds: mockData.feeds[group] || [] })
});
// Post Feed Info
app.post('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    
    const newGroup = req.body;
    newGroup.name = newGroup.name || 'new_group_' + Date.now();
    newGroup.num_feeds = 0;
    newGroup.status = true;
    newGroup.description = newGroup.description || '새로운 그룹';
    
    mockData.groups.groups.push(newGroup);
    res.json({ status: 'success', group: newGroup });
});
// Delete Feed Info
app.delete('/groups/:group/feeds/:feed', (req, res) => {
    const { group, feed } = req.params;
    
    const feedIndex = mockData.feeds[req.params.group]?.findIndex(f => f.name === req.params.feed);
    if (feedIndex !== -1) {
        const deletedFeed = mockData.feeds[req.params.group].splice(feedIndex, 1)[0];
        res.json({ status: 'success', message: 'Feed deleted', feed: deletedFeed });
    } else {
        res.status(404).json({ status: 'error', message: 'Feed not found' });
    }
});
// Get Feeds By Group
app.get('/groups/:group/feeds', (req, res) => {
    const { group } = req.params;
    res.json({ status: 'success', message: 'Get Feeds By Group - Mock response' })
});
// Remove Group
app.delete('/groups/:group', (req, res) => {
    const { group } = req.params;
    
    const groupIndex = mockData.groups.groups.findIndex(g => g.name === req.params.group);
    if (groupIndex !== -1) {
        const deletedGroup = mockData.groups.groups.splice(groupIndex, 1)[0];
        delete mockData.feeds[req.params.group];
        res.json({ status: 'success', message: 'Group deleted', group: deletedGroup });
    } else {
        res.status(404).json({ status: 'error', message: 'Group not found' });
    }
});
// Get Groups
app.get('/groups', (req, res) => {
    const {  } = req.params;
    res.json(mockData.groups)
});

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json({ 
    status: 'failure', 
    message: `Endpoint ${req.method} ${req.originalUrl} not found` 
  });
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Mock API Server running on http://localhost:${PORT}`);
  console.log(`📁 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 API URL: ${process.env.VUE_APP_API_URL || `http://localhost:${PORT}`}`);
  console.log(`📊 Mock data loaded: ${Object.keys(mockData).length} categories`);
});