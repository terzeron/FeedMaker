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
      sdkLoadError: null,
      initializationAttempted: false,
    };
  },
  props: {
    appId: {
      type: String,
      default: process.env.VUE_APP_FACEBOOK_APP_ID || "test_app_id",
    },
    version: {
      type: String,
      default: "v14.0",
    },
  },
  methods: {
    loadFacebookSDK() {
      console.log("Loading Facebook SDK...");
      console.log("App ID:", this.appId);
      console.log("Version:", this.version);
      console.log("Environment VUE_APP_FACEBOOK_APP_ID:", process.env.VUE_APP_FACEBOOK_APP_ID);

      if (!this.appId || this.appId === "test_app_id") {
        console.warn("Facebook App ID is not configured. Please set VUE_APP_FACEBOOK_APP_ID in your .env file");
        this.sdkLoadError = "Facebook App ID is not configured";
        return Promise.reject(new Error("Facebook App ID is not configured"));
      }

      this.initializationAttempted = true;

      return new Promise((resolve, reject) => {
        // Check if SDK is already loaded
        if (window.FB) {
          console.log("Facebook SDK already loaded");
          this.isSdkLoaded = true;
          this.$emit('auth-initialized');
          resolve();
          return;
        }

        // Check if fbAsyncInit is already set
        if (window.fbAsyncInit) {
          console.log("fbAsyncInit already set, waiting for initialization...");
          // Wait a bit for initialization to complete
          setTimeout(() => {
            if (window.FB) {
              console.log("Facebook SDK initialized via existing fbAsyncInit");
              this.isSdkLoaded = true;
              this.$emit('auth-initialized');
              resolve();
            } else {
              reject(new Error("Facebook SDK initialization timeout"));
            }
          }, 2000);
          return;
        }

        window.fbAsyncInit = () => {
          console.log("Facebook SDK initialized");
          window.FB.init({
            appId: this.appId,
            cookie: true,
            xfbml: true,
            version: this.version
          });

          this.isSdkLoaded = true;
          this.$emit('auth-initialized');
          resolve();
        };

        (function(d, s, id){
          const fjs = d.getElementsByTagName(s)[0];
          if (d.getElementById(id)) { 
            console.log("Facebook SDK script already exists");
            return; 
          }
          const js = d.createElement(s);
          js.id = id;
          js.src = "https://connect.facebook.net/en_US/sdk.js";
          js.onload = () => {
            console.log("Facebook SDK script loaded");
          };
          js.onerror = (error) => {
            console.error("Facebook SDK script load error:", error);
            this.sdkLoadError = "Failed to load Facebook SDK";
            reject(error);
          };
          fjs.parentNode.insertBefore(js, fjs);
        })(document, 'script', 'facebook-jssdk');
      });
    },
    async login() {
      console.log("Attempting Facebook login...");
      console.log("SDK loaded:", this.isSdkLoaded);
      console.log("Window FB:", !!window.FB);
      
      if (!this.isSdkLoaded || !window.FB) {
        throw new Error("Facebook SDK is not loaded");
      }

      const loginOptions = {
        scope: 'public_profile, email', // 필요한 권한 지정
      };
      
      try {
        return new Promise((resolve, reject) => {
          window.FB.login(function (response) {
            console.log("Facebook login response:", response);
            if (response.authResponse) {
              if (response.status === "connected") {
                console.log("Login succeeded: ", response.authResponse.accessToken);
                resolve(response.authResponse.accessToken);
              } else {
                reject("Login failed: " + response.status);
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
      console.log("Attempting Facebook logout...");
      
      if (!this.isSdkLoaded || !window.FB) {
        throw new Error("Facebook SDK is not loaded");
      }

      const logoutPromise = () => {
        return new Promise((resolve) => {
          window.FB.getLoginStatus(function (response) {
            if (response && response.status === 'connected') {
              window.FB.logout(function (response) {
                console.log("Logout response:", response);
                resolve(response);
              });
            } else {
              resolve(response);
            }
          });
        })
      };
      await logoutPromise();
    },
    async getProfile() {
      console.log("Getting Facebook profile...");
      
      if (!this.isSdkLoaded || !window.FB) {
        throw new Error("Facebook SDK is not loaded");
      }

      const profilePromise = () => {
        return new Promise((resolve, reject) => {
          window.FB.api("/me", {fields: 'name,email'}, function (response) {
            console.log("Profile response:", response);
            if (response && !response.error) {
              resolve(response);
            } else {
              reject("can't get profile: " + (response.error ? response.error.message : "unknown error"));
            }
          });
        })
      }
      return await profilePromise();
    },
    // 초기화 상태 확인 메서드 추가
    isInitialized() {
      return this.isSdkLoaded && !!window.FB;
    },
  },
  mounted: async function () {
    console.log("FacebookAuth component mounted");
    console.log("Component props:", {
      appId: this.appId,
      version: this.version
    });
    
    try {
      await this.loadFacebookSDK();
    } catch (error) {
      console.error("Error loading Facebook SDK", error);
      this.sdkLoadError = error.message;
    }
  },
};
</script>
