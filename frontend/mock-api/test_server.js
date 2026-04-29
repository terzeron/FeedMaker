const express = require('express');
const app = express();
const PORT = 3000;
const {
  createFailure,
  createGroupsResponse,
  createFeedsResponse,
  createProblemsResponse
} = require('./contracts');

const mockGroups = [
  { name: 'webtoon', num_feeds: 2, status: true, description: '웹툰 피드 그룹' },
  { name: '_disabled_group', num_feeds: 1, status: false, description: '비활성화된 그룹' }
];

const mockFeeds = {
  webtoon: [
    { name: 'naver_webtoon', title: '네이버 웹툰', status: true, description: '네이버 웹툰 피드' },
    { name: '_disabled_feed', title: '비활성화 피드', status: false, description: '비활성화된 피드' }
  ],
  _disabled_group: [
    { name: 'legacy_feed', title: '레거시 피드', status: false, description: '레거시 피드' }
  ]
};

function buildProblemResult(type) {
  if (type === 'status_info') {
    return [
      {
        group_name: 'webtoon',
        feed_name: 'naver_webtoon',
        feed_title: '네이버 웹툰',
        http_request: true,
        public_html: true,
        feedmaker: true,
        update_date: '2026-04-29',
        upload_date: '2026-04-29',
        access_date: '2026-04-29',
        view_date: '2026-04-29'
      }
    ];
  }

  if (type === 'public_feed_info') {
    return [
      {
        group_name: 'webtoon',
        feed_name: 'naver_webtoon',
        feed_title: '네이버 웹툰',
        file_size: 4096,
        num_items: 8,
        upload_date: '2026-04-29T00:00:00'
      }
    ];
  }

  return [];
}

// CORS 설정
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

// 간단한 라우트들
app.get('/groups', (req, res) => {
  res.json(createGroupsResponse(mockGroups));
});

app.get('/groups/:group/feeds', (req, res) => {
  const { group } = req.params;
  res.json(createFeedsResponse(mockFeeds[group] || []));
});

app.get('/problems/:type', (req, res) => {
  const { type } = req.params;
  res.json(createProblemsResponse(buildProblemResult(type)));
});

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json(createFailure(`Endpoint ${req.method} ${req.originalUrl} not found`));
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Test Mock API Server running on http://localhost:${PORT}`);
}); 
