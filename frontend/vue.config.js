const fs = require('fs');
const { execSync } = require('child_process');

// 빌드 시점에 버전 정보 생성
function generateVersionInfo() {
  try {
    // 현재 날짜와 시간 (한국 시간)
    const now = new Date();
    const kstDate = new Date(now.getTime() + (9 * 60 * 60 * 1000)); // UTC+9
    const datetime = kstDate.toISOString().replace('T', ' ').substring(0, 19);

    // Git commit hash 가져오기 (여러 방법 시도)
    let commitHash = 'unknown';

    // 방법 1: 환경변수에서 가져오기 (CI/CD에서 설정)
    if (process.env.GIT_COMMIT) {
      commitHash = process.env.GIT_COMMIT.substring(0, 7);
    } else if (process.env.COMMIT_SHA) {
      commitHash = process.env.COMMIT_SHA.substring(0, 7);
    } else if (process.env.GITHUB_SHA) {
      commitHash = process.env.GITHUB_SHA.substring(0, 7);
    } else {
      // 방법 2: Git 명령어로 가져오기
      try {
        // 현재 디렉토리가 아니라 상위 디렉토리에서 시도
        const options = { encoding: 'utf8', cwd: process.cwd() };
        commitHash = execSync('git rev-parse --short HEAD', options).trim();
      } catch (gitError) {
        try {
          // 상위 디렉토리에서 시도
          const options = { encoding: 'utf8', cwd: require('path').resolve('..') };
          commitHash = execSync('git rev-parse --short HEAD', options).trim();
        } catch (parentGitError) {
          // 방법 3: .git/HEAD 파일 직접 읽기
          try {
            const path = require('path');
            const gitHeadPath = path.resolve('.git/HEAD');
            if (fs.existsSync(gitHeadPath)) {
              const headContent = fs.readFileSync(gitHeadPath, 'utf8').trim();
              if (headContent.startsWith('ref: ')) {
                const refPath = path.resolve('.git', headContent.substring(5));
                if (fs.existsSync(refPath)) {
                  commitHash = fs.readFileSync(refPath, 'utf8').trim().substring(0, 7);
                }
              } else {
                commitHash = headContent.substring(0, 7);
              }
            } else {
              // 상위 디렉토리의 .git 확인
              const parentGitHeadPath = path.resolve('../.git/HEAD');
              if (fs.existsSync(parentGitHeadPath)) {
                const headContent = fs.readFileSync(parentGitHeadPath, 'utf8').trim();
                if (headContent.startsWith('ref: ')) {
                  const refPath = path.resolve('../.git', headContent.substring(5));
                  if (fs.existsSync(refPath)) {
                    commitHash = fs.readFileSync(refPath, 'utf8').trim().substring(0, 7);
                  }
                } else {
                  commitHash = headContent.substring(0, 7);
                }
              }
            }
          } catch (fileError) {
            console.warn('Warning: Could not read git info from files:', fileError.message);
          }
        }
      }
    }

    console.log(`Build version: ${datetime} (${commitHash})`);
    return `${datetime} (${commitHash})`;
  } catch (error) {
    console.error('Error generating version info:', error);
    const fallbackTime = new Date().toISOString().replace('T', ' ').substring(0, 19);
    return `${fallbackTime} (unknown)`;
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
