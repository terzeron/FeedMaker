#!/usr/bin/env node
const { execSync } = require('child_process');

// Git commit hash를 환경변수로 설정하고 빌드 실행
try {
  // Git commit hash 가져오기
  let commitHash = 'unknown';
  try {
    commitHash = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim();
    console.log(`Setting GIT_COMMIT=${commitHash}`);
  } catch (error) {
    console.warn('Warning: Could not get git commit hash, using "unknown"');
  }
  
  // 환경변수 설정
  process.env.GIT_COMMIT = commitHash;
  
  // Vue CLI 빌드 실행
  console.log('Starting Vue CLI build...');
  execSync('npx vue-cli-service build', { 
    stdio: 'inherit',
    env: { ...process.env, GIT_COMMIT: commitHash }
  });
  
  console.log('Build completed successfully!');
} catch (error) {
  console.error('Build failed:', error.message);
  process.exit(1);
}