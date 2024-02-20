<template>
  <div>
    <p>로그인 중...</p>
  </div>
</template>

<script>
export default {
  name: 'AuthCallback',
  mounted() {
    // OAuth 인증 후에 이 페이지가 호출됩니다.
    // 여기서 필요한 작업을 수행하고, 사용자의 인증 정보를 처리하세요.

    // 예를 들어, URL에서 액세스 토큰을 가져올 수 있습니다.
    const accessToken = this.$route.query.access_token;

    if (accessToken) {
      // 액세스 토큰을 받았을 때의 처리를 여기에 추가합니다.
      // 로그인 상태를 설정하거나, 사용자 정보를 가져오는 등의 작업을 수행하세요.
    }

    // 필요한 작업을 마치고 다음 페이지로 이동하거나 리디렉션할 수 있습니다.
    // 예를 들어, 로그인 완료 후 홈 페이지로 리디렉션할 수 있습니다.
    this.$router.push({ name: 'ExecResult' });
  },
};
</script>
