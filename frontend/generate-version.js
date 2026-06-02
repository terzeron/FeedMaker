#!/usr/bin/env node
const { execSync } = require("child_process");

function generateVersionInfo() {
  try {
    // 현재 날짜와 시간 (한국 시간)
    const now = new Date();
    const kstDate = new Date(now.getTime() + 9 * 60 * 60 * 1000); // UTC+9
    const datetime = kstDate.toISOString().replace("T", " ").substring(0, 19);

    // Git commit hash 가져오기.
    // 빌드 컨텍스트(.dockerignore가 .git 제외)에서는 git 명령이 실패하므로
    // build-arg로 주입된 GIT_COMMIT 환경변수를 우선 사용한다(build-with-version.js와 동일 규약).
    let commitHash = process.env.GIT_COMMIT || "unknown";
    if (commitHash === "unknown") {
      try {
        commitHash = execSync("git rev-parse --short HEAD", {
          encoding: "utf8",
        }).trim();
      } catch (error) {
        console.warn("Warning: Could not get git commit hash:", error.message);
      }
    }

    // 환경변수 설정용 문자열 생성
    const versionString = `${datetime} (${commitHash})`;

    // 환경변수로 설정
    process.env.VUE_APP_VERSION = versionString;
    process.env.VUE_APP_BUILD_DATE = datetime;
    process.env.VUE_APP_COMMIT_HASH = commitHash;

    console.log("Version info generated:", versionString);
    return versionString;
  } catch (error) {
    console.error("Error generating version info:", error);
    const fallbackVersion = `${new Date().toISOString().replace("T", " ").substring(0, 19)} (unknown)`;
    process.env.VUE_APP_VERSION = fallbackVersion;
    return fallbackVersion;
  }
}

module.exports = generateVersionInfo;
