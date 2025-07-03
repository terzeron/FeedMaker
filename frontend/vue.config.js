const fs = require('fs');
const { execSync } = require('child_process');

// 빌드 시점에 버전 정보 생성
function generateVersionInfo() {
  try {
    // 현재 날짜와 시간 (한국 시간)
    const now = new Date();
    const kstDate = new Date(now.getTime() + (9 * 60 * 60 * 1000)); // UTC+9
    const datetime = kstDate.toISOString().replace('T', ' ').substring(0, 19);
    
    // Git commit hash 가져오기
    let commitHash = 'unknown';
    try {
      commitHash = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim();
    } catch (error) {
      console.warn('Warning: Could not get git commit hash:', error.message);
    }
    
    return `${datetime} (${commitHash})`;
  } catch (error) {
    console.error('Error generating version info:', error);
    return `${new Date().toISOString().replace('T', ' ').substring(0, 19)} (unknown)`;
  }
}

module.exports = {
    runtimeCompiler: true,
    css: {
        extract: process.env.NODE_ENV === 'production', // 개발 모드에서는 CSS 추출 비활성화
        sourceMap: true
    },
    devServer: {
        port: 8081,
        allowedHosts: "all",
        https: true
    },
    configureWebpack: {
        optimization: {
            splitChunks: {
                chunks: 'all',
                maxSize: 244 * 1024, // 244 KiB
            },
        },
        plugins: [
            new (require('webpack')).DefinePlugin({
                'process.env.VUE_APP_VERSION': JSON.stringify(generateVersionInfo())
            })
        ]
    }
}
