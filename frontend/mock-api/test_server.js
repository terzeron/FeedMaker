const express = require('express');
const app = express();
const PORT = 3000;

// CORS 설정
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

// 간단한 라우트들
app.get('/groups', (req, res) => {
  res.json({ status: 'success', message: 'Get Groups - Mock response' });
});

app.get('/groups/:group/feeds', (req, res) => {
  const { group } = req.params;
  res.json({ status: 'success', message: `Get Feeds for group: ${group}` });
});

app.get('/problems/:type', (req, res) => {
  const { type } = req.params;
  res.json({ status: 'success', message: `Get Problems for type: ${type}` });
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
  console.log(`🚀 Test Mock API Server running on http://localhost:${PORT}`);
}); 