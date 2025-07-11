#!/usr/bin/env python3
"""
OpenAPI 스펙을 올바르게 분석해서 Mock API 서버를 업데이트하는 스크립트
"""

import json
import re
import sys
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def convert_openapi_path_to_express(path: str) -> str:
    """
    OpenAPI 경로 형식을 Express.js 형식으로 변환
    예: /groups/{group_name}/feeds -> /groups/:group/feeds
    """
    # {param} -> :param 형식으로 변환 (단순한 형태로)
    express_path = re.sub(r'\{([^}]+)\}', r':\1', path)
    # 복잡한 파라미터 이름을 단순하게 변환
    express_path = express_path.replace(':group_name', ':group')
    express_path = express_path.replace(':feed_name', ':feed')
    express_path = express_path.replace(':data_type', ':type')
    express_path = express_path.replace(':html_file_name', ':file')
    return express_path

def generate_mock_data() -> Dict[str, Any]:
    """
    다양한 mock 데이터를 생성합니다.
    """
    # 그룹 데이터
    groups = [
        {"name": "webtoon", "num_feeds": 3, "status": True, "description": "웹툰 피드 그룹"},
        {"name": "news", "num_feeds": 2, "status": True, "description": "뉴스 피드 그룹"},
        {"name": "blog", "num_feeds": 1, "status": False, "description": "블로그 피드 그룹"},
        {"name": "tech", "num_feeds": 2, "status": True, "description": "기술 관련 피드 그룹"},
        {"name": "sports", "num_feeds": 1, "status": True, "description": "스포츠 피드 그룹"},
        {"name": "entertainment", "num_feeds": 2, "status": True, "description": "엔터테인먼트 피드 그룹"},
        {"name": "_disabled_group", "num_feeds": 0, "status": False, "description": "비활성화된 그룹"}
    ]
    
    # 피드 데이터
    feeds = {
        "webtoon": [
            {"name": "naver_webtoon", "title": "네이버 웹툰", "status": True, "description": "네이버 웹툰 피드"},
            {"name": "kakao_webtoon", "title": "카카오 웹툰", "status": True, "description": "카카오 웹툰 피드"},
            {"name": "lezhin_webtoon", "title": "레진 웹툰", "status": True, "description": "레진 웹툰 피드"},
            {"name": "_disabled_webtoon", "title": "비활성화 웹툰", "status": False, "description": "비활성화된 웹툰 피드"}
        ],
        "news": [
            {"name": "tech_news", "title": "기술 뉴스", "status": True, "description": "기술 뉴스 피드"},
            {"name": "sports_news", "title": "스포츠 뉴스", "status": True, "description": "스포츠 뉴스 피드"},
            {"name": "politics_news", "title": "정치 뉴스", "status": True, "description": "정치 뉴스 피드"}
        ],
        "blog": [
            {"name": "personal_blog", "title": "개인 블로그", "status": False, "description": "개인 블로그 피드"}
        ],
        "tech": [
            {"name": "github_trending", "title": "GitHub Trending", "status": True, "description": "GitHub 트렌딩 저장소"},
            {"name": "stackoverflow", "title": "Stack Overflow", "status": True, "description": "Stack Overflow 질문"},
            {"name": "dev_to", "title": "Dev.to", "status": True, "description": "Dev.to 개발자 블로그"}
        ],
        "sports": [
            {"name": "soccer_news", "title": "축구 뉴스", "status": True, "description": "축구 관련 뉴스"}
        ],
        "entertainment": [
            {"name": "movie_reviews", "title": "영화 리뷰", "status": True, "description": "최신 영화 리뷰"},
            {"name": "music_news", "title": "음악 뉴스", "status": True, "description": "음악 관련 뉴스"}
        ]
    }
    
    # 문제 데이터
    problems = [
        {
            "id": str(uuid.uuid4()),
            "type": "connection_error",
            "severity": "high",
            "message": "네이버 웹툰 서버 연결 실패",
            "feed_name": "naver_webtoon",
            "group_name": "webtoon",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "status": "open"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "parsing_error",
            "severity": "medium",
            "message": "카카오 웹툰 HTML 파싱 오류",
            "feed_name": "kakao_webtoon",
            "group_name": "webtoon",
            "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
            "status": "resolved"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "timeout_error",
            "severity": "low",
            "message": "GitHub API 응답 시간 초과",
            "feed_name": "github_trending",
            "group_name": "tech",
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "status": "open"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "data_validation_error",
            "severity": "medium",
            "message": "스포츠 뉴스 데이터 형식 오류",
            "feed_name": "sports_news",
            "group_name": "news",
            "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
            "status": "open"
        }
    ]
    
    # 실행 결과 데이터
    exec_results = [
        {
            "feed_name": "naver_webtoon",
            "group_name": "webtoon",
            "status": "success",
            "start_time": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "end_time": (datetime.now() - timedelta(minutes=25)).isoformat(),
            "items_processed": 15,
            "items_success": 15,
            "items_failed": 0,
            "log": "Feed processing completed successfully"
        },
        {
            "feed_name": "kakao_webtoon",
            "group_name": "webtoon",
            "status": "partial_success",
            "start_time": (datetime.now() - timedelta(minutes=20)).isoformat(),
            "end_time": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "items_processed": 8,
            "items_success": 7,
            "items_failed": 1,
            "log": "Feed processing completed with 1 error"
        },
        {
            "feed_name": "github_trending",
            "group_name": "tech",
            "status": "failed",
            "start_time": (datetime.now() - timedelta(minutes=10)).isoformat(),
            "end_time": (datetime.now() - timedelta(minutes=8)).isoformat(),
            "items_processed": 0,
            "items_success": 0,
            "items_failed": 0,
            "log": "API rate limit exceeded"
        }
    ]
    
    # 피드 정보 데이터
    feed_infos = {}
    for group_name, group_feeds in feeds.items():
        for feed in group_feeds:
            if feed["status"]:
                feed_key = f"{group_name}/{feed['name']}"
                feed_infos[feed_key] = {
                    "config": {
                        "collection": {
                            "list_url_list": [f"https://example.com/{feed['name']}"],
                            "feed_dir_path": f"/feeds/{group_name}/{feed['name']}",
                            "feed_name": feed['name']
                        },
                        "rss": {
                            "title": feed['title'],
                            "description": f"{feed['title']} 최신 업데이트",
                            "link": f"https://terzeron.com/{feed['name']}.xml"
                        },
                        "extraction": {
                            "list_url": f"https://example.com/{feed['name']}",
                            "list_url_parser": feed['name']
                        }
                    },
                    "collection_info": {
                        "num_collection_urls": random.randint(5, 20),
                        "collect_date": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                        "urllist_count": random.randint(5, 20),
                        "total_item_count": random.randint(5, 20)
                    },
                    "public_feed_info": {
                        "num_items_in_result": random.randint(5, 20),
                        "size_of_result_file": random.randint(1024, 4096),
                        "last_upload_date": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat()
                    },
                    "progress_info": {
                        "current_index": random.randint(1, 10),
                        "total_item_count": random.randint(10, 20),
                        "unit_size_per_day": random.randint(1, 5),
                        "progress_ratio": random.uniform(0, 100),
                        "feed_completion_due_date": (datetime.now() + timedelta(days=random.randint(1, 7))).isoformat()
                    }
                }
    
    return {
        "groups": {"groups": groups},
        "feeds": feeds,
        "problems": {"problems": problems},
        "exec_result": {"exec_result": exec_results},
        "feed_info": feed_infos
    }

def analyze_openapi_spec(openapi_file: str = "../../openapi.json") -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """
    OpenAPI 스펙을 분석하여 엔드포인트 목록을 추출합니다.
    """
    try:
        with open(openapi_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        endpoints = []
        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                summary = details.get('summary', 'No description')
                operation_id = details.get('operationId', '')
                express_path = convert_openapi_path_to_express(path)
                
                endpoints.append({
                    'original_path': path,
                    'express_path': express_path,
                    'method': method.upper(),
                    'summary': summary,
                    'operation_id': operation_id
                })
        
        return endpoints, spec
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"❌ OpenAPI 스펙 분석 실패: {e}")
        return None, None

def generate_mock_response(endpoint: Dict[str, Any], mock_data: Dict[str, Any]) -> str:
    """
    엔드포인트에 맞는 mock 응답을 생성합니다.
    """
    path = endpoint['express_path']
    method = endpoint['method']
    summary = endpoint['summary']
    
    # 경로 파라미터 추출
    path_params = re.findall(r':([^/]+)', path)
    
    # 기본 응답 템플릿
    if method == 'GET':
        if '/groups' in path and '/feeds' not in path:
            return "res.json(mockData.groups)"
        elif '/groups' in path and '/feeds' in path and len(path_params) >= 2:
            group_param = path_params[0]
            return f"res.json({{ feeds: mockData.feeds[{group_param}] || [] }})"
        elif '/problems' in path:
            return "res.json(mockData.problems)"
        elif '/exec-result' in path:
            return "res.json(mockData.exec_result)"
        elif '/feed-info' in path and len(path_params) >= 2:
            group_param = path_params[0]
            feed_param = path_params[1]
            return f"res.json({{ feed_info: mockData.feed_info[`${{groupParam}}/${{feedParam}}`] || {{}} }})"
        elif '/search' in path:
            query = "req.query.q || ''"
            return f"""
    const query = {query};
    const results = [];
    
    // 그룹에서 검색
    mockData.groups.groups.forEach(group => {{
        if (group.name.toLowerCase().includes(query.toLowerCase()) || 
            group.description.toLowerCase().includes(query.toLowerCase())) {{
            results.push({{ type: 'group', data: group }});
        }}
    }});
    
    // 피드에서 검색
    Object.entries(mockData.feeds).forEach(([groupName, feeds]) => {{
        feeds.forEach(feed => {{
            if (feed.name.toLowerCase().includes(query.toLowerCase()) || 
                feed.title.toLowerCase().includes(query.toLowerCase()) ||
                feed.description.toLowerCase().includes(query.toLowerCase())) {{
                results.push({{ type: 'feed', data: feed, group: groupName }});
            }}
        }});
    }});
    
    res.json({{ results: results.slice(0, 10) }});"""
        else:
            return f"res.json({{ status: 'success', message: '{summary} - Mock response' }})"
    
    elif method == 'POST':
        if '/groups' in path:
            return """
    const newGroup = req.body;
    newGroup.name = newGroup.name || 'new_group_' + Date.now();
    newGroup.num_feeds = 0;
    newGroup.status = true;
    newGroup.description = newGroup.description || '새로운 그룹';
    
    mockData.groups.groups.push(newGroup);
    res.json({ status: 'success', group: newGroup });"""
        elif '/feeds' in path:
            return """
    const newFeed = req.body;
    newFeed.name = newFeed.name || 'new_feed_' + Date.now();
    newFeed.status = true;
    newFeed.description = newFeed.description || '새로운 피드';
    
    const groupName = req.params.group;
    if (!mockData.feeds[groupName]) {
        mockData.feeds[groupName] = [];
    }
    mockData.feeds[groupName].push(newFeed);
    
    res.json({ status: 'success', feed: newFeed });"""
        elif '/run' in path:
            return """
    const execResult = {
        feed_name: req.params.feed,
        group_name: req.params.group,
        status: 'success',
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        items_processed: Math.floor(Math.random() * 20) + 5,
        items_success: Math.floor(Math.random() * 20) + 5,
        items_failed: 0,
        log: 'Feed processing completed successfully'
    };
    res.json({ status: 'success', result: execResult });"""
        else:
            return f"res.json({{ status: 'success', message: '{summary} - Mock response' }})"
    
    elif method == 'PUT':
        if '/groups' in path and '/toggle' in path:
            return """
    const groupIndex = mockData.groups.groups.findIndex(g => g.name === req.params.group);
    if (groupIndex !== -1) {
        mockData.groups.groups[groupIndex].status = !mockData.groups.groups[groupIndex].status;
        res.json({ status: 'success', group: mockData.groups.groups[groupIndex] });
    } else {
        res.status(404).json({ status: 'error', message: 'Group not found' });
    }"""
        elif '/feeds' in path and '/toggle' in path:
            return """
    const feedIndex = mockData.feeds[req.params.group]?.findIndex(f => f.name === req.params.feed);
    if (feedIndex !== -1) {
        mockData.feeds[req.params.group][feedIndex].status = !mockData.feeds[req.params.group][feedIndex].status;
        res.json({ status: 'success', feed: mockData.feeds[req.params.group][feedIndex] });
    } else {
        res.status(404).json({ status: 'error', message: 'Feed not found' });
    }"""
        elif '/groups' in path and '/site_config' in path:
            return """
    res.json({ status: 'success', message: 'Site config updated' });"""
        else:
            return f"res.json({{ status: 'success', message: '{summary} - Mock response' }})"
    
    elif method == 'DELETE':
        if '/groups' in path and '/feeds' in path and '/htmls' in path:
            return """
    res.json({ status: 'success', message: 'HTML file removed' });"""
        elif '/groups' in path and '/feeds' in path and '/list' in path:
            return """
    res.json({ status: 'success', message: 'List removed' });"""
        elif '/groups' in path and '/feeds' in path:
            return """
    const feedIndex = mockData.feeds[req.params.group]?.findIndex(f => f.name === req.params.feed);
    if (feedIndex !== -1) {
        const deletedFeed = mockData.feeds[req.params.group].splice(feedIndex, 1)[0];
        res.json({ status: 'success', message: 'Feed deleted', feed: deletedFeed });
    } else {
        res.status(404).json({ status: 'error', message: 'Feed not found' });
    }"""
        elif '/groups' in path:
            return """
    const groupIndex = mockData.groups.groups.findIndex(g => g.name === req.params.group);
    if (groupIndex !== -1) {
        const deletedGroup = mockData.groups.groups.splice(groupIndex, 1)[0];
        delete mockData.feeds[req.params.group];
        res.json({ status: 'success', message: 'Group deleted', group: deletedGroup });
    } else {
        res.status(404).json({ status: 'error', message: 'Group not found' });
    }"""
        elif '/public_feeds' in path:
            return """
    res.json({ status: 'success', message: 'Public feed removed' });"""
        else:
            return f"res.json({{ status: 'success', message: '{summary} - Mock response' }})"
    
    else:
        return f"res.json({{ status: 'success', message: '{summary} - Mock response' }})"

def generate_server_js(endpoints: List[Dict[str, Any]]) -> str:
    """
    완전한 server.js 파일을 생성합니다.
    """
    # Mock 데이터 생성
    mock_data = generate_mock_data()
    
    server_template = '''const express = require('express');
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
const mockData = ''' + json.dumps(mock_data, ensure_ascii=False, indent=2) + ''';

// 로깅 미들웨어
app.use((req, res, next) => {
  console.log(`[Mock API] ${req.method} ${req.url}`);
  next();
});

// OpenAPI 스펙에 따른 라우팅 처리
'''
    
    # 각 엔드포인트에 대한 라우트 코드 생성
    for endpoint in endpoints:
        express_path = endpoint['express_path']
        method = endpoint['method'].lower()
        summary = endpoint['summary']
        
        # 경로 파라미터 추출 (Express 형식)
        path_params = re.findall(r':([^/]+)', express_path)
        
        # 파라미터 변수명을 그대로 사용 (camelCase 변환 제거)
        param_vars = path_params
        
        # Mock 응답 생성
        mock_response = generate_mock_response(endpoint, mock_data)
        
        # Express.js 라우트 코드 생성
        route_code = f'''
// {summary}
app.{method}('{express_path}', (req, res) => {{
    const {{ {', '.join(param_vars)} }} = req.params;
    {mock_response}
}});'''
        
        server_template += route_code
    
    # 404 핸들러와 서버 시작 코드 추가
    server_template += '''

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
});'''
    
    return server_template

def update_db_json() -> None:
    """
    db.json 파일을 새로운 mock 데이터로 업데이트합니다.
    """
    mock_data = generate_mock_data()
    
    # 기존 db.json 백업
    if Path("db.json").exists():
        import shutil
        shutil.copy("db.json", "db.json.backup")
        print("💾 기존 db.json을 db.json.backup으로 백업했습니다.")
    
    # 새로운 db.json 파일 저장
    with open('db.json', 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)
    
    print("✅ 새로운 db.json 파일이 생성되었습니다!")

def main() -> None:
    print("🔍 OpenAPI 스펙 분석 중...")
    endpoints, spec = analyze_openapi_spec()
    
    if not endpoints:
        print("❌ OpenAPI 스펙을 읽을 수 없습니다.")
        sys.exit(1)
    
    print(f"✅ 총 {len(endpoints)}개의 엔드포인트를 발견했습니다.")
    
    print("\n📋 발견된 엔드포인트:")
    for endpoint in endpoints:
        print(f"  {endpoint['method']} {endpoint['original_path']} -> {endpoint['express_path']} - {endpoint['summary']}")
    
    # db.json 파일 업데이트
    print("\n📊 Mock 데이터 생성 중...")
    update_db_json()
    
    # 완전한 server.js 파일 생성
    print("\n🔧 server.js 파일 생성 중...")
    server_js_content = generate_server_js(endpoints)
    
    # 기존 server.js 백업
    if Path("server.js").exists():
        import shutil
        shutil.copy("server.js", "server.js.backup")
        print("💾 기존 server.js를 server.js.backup으로 백업했습니다.")
    
    # 새로운 server.js 파일 저장
    with open('server.js', 'w', encoding='utf-8') as f:
        f.write(server_js_content)
    
    print("✅ 새로운 server.js 파일이 생성되었습니다!")
    print("🚀 이제 'npm run mock:api'로 서버를 실행할 수 있습니다.")
    print("📊 다양한 mock 데이터가 포함되어 있어 더 현실적인 테스트가 가능합니다.")

if __name__ == "__main__":
    main() 