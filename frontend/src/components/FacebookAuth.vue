<template>
  <span>
    <!-- Left empty intentionally -->
  </span>
</template>

<script>
export default {
  name: "FacebookAuth",
  data: function () {
    return {
      isSdkLoaded: false,
    };
  },
  props: {
    appId: {
      type: String,
      default: process.env.VUE_APP_FACEBOOK_APP_ID,
    },
    version: {
      type: String,
      default: "v14.0",
    },
  },
  methods: {
    loadFacebookSDK() {
      if (!this.appId || !this.version) {
        throw new Error("Facebook appId and version props are required");
      }

      return new Promise((resolve, reject) => {
        window.fbAsyncInit = () => {
          window.FB.init({
            appId: this.appId,
            cookie: true,
            xfbml: true,
            version: this.version
          });

          this.$emit('auth-initialized');
        };

        (function(d, s, id){
          const fjs = d.getElementsByTagName(s)[0];
          if (d.getElementById(id)) { return; }
          const js = d.createElement(s);
          js.id = id;
          js.src = "https://connect.facebook.net/en_US/sdk.js";
          js.onload = resolve;
          js.onerror = reject;
          fjs.parentNode.insertBefore(js, fjs);
        })(document, 'script', 'facebook-jssdk');
      });
    },
    async login() {
      const loginOptions = {
        scope: 'public_profile, email', // 필요한 권한 지정
      };
      try {
        return new Promise((resolve, reject) => {
          window.FB.login(function (response) {
            if (response.authResponse) {
              if (response.status === "connected") {
                console.log("Login succeeded: ", response.authResponse.accessToken);
                resolve(response.authResponse.accessToken);
              }
            } else {
              reject("User cancelled login or did not fully authorize.");
            }
          }, loginOptions);
        });
      } catch (error) {
        console.error("Login failed: ", error);
        throw error;
      }
    },
    async logout() {
      const logoutPromise = () => {
        return new Promise((resolve) => {
          window.FB.getLoginStatus(function (response) {
            if (response && response.status === 'connected') {
              window.FB.logout(function (response) {
                resolve(response);
              });
            }
          });
        })
      };
      await logoutPromise();
    },
    async getProfile() {
      const profilePromise = () => {
        return new Promise((resolve, reject) => {
          window.FB.api("/me", {fields: 'name,email'}, function (response) {
            if (response) {
              resolve(response);
            } else {
              reject("can't get profile");
            }
          });
        })
      }
      return await profilePromise();
    },
  },
  // FacebookAuth.vue
  mounted: async function () {
    this.loadFacebookSDK().catch(error => {
      console.error("Error loading Facebook SDK", error);
    });
  },
};
</script>
