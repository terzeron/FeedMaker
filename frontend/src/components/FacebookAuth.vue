<template>
  <span>
    <!-- Left empty intentionally -->
  </span>
</template>

<script setup>
import { ref, onMounted } from 'vue';

defineOptions({
  name: 'FacebookAuth'
});

// Props
const props = defineProps({
  appId: {
    type: String,
    default: process.env.VUE_APP_FACEBOOK_APP_ID || 'test_app_id'
  },
  version: {
    type: String,
    default: 'v14.0'
  }
});

// Emits
const emit = defineEmits(['auth-initialized']);

// Reactive state
const isSdkLoaded = ref(false);
const sdkLoadError = ref(null);
const initializationAttempted = ref(false);

// Methods
const loadFacebookSDK = () => {
  console.log('Loading Facebook SDK...');
  console.log('App ID:', props.appId);
  console.log('Version:', props.version);
  console.log('Environment VUE_APP_FACEBOOK_APP_ID:', process.env.VUE_APP_FACEBOOK_APP_ID);

  if (!props.appId || props.appId === 'test_app_id') {
    console.warn('Facebook App ID is not configured. Please set VUE_APP_FACEBOOK_APP_ID in your .env file');
    sdkLoadError.value = 'Facebook App ID is not configured';
    return Promise.reject(new Error('Facebook App ID is not configured'));
  }

  initializationAttempted.value = true;

  return new Promise((resolve, reject) => {
    // Check if SDK is already loaded
    if (window.FB) {
      console.log('Facebook SDK already loaded');
      isSdkLoaded.value = true;
      emit('auth-initialized');
      resolve();
      return;
    }

    // Check if fbAsyncInit is already set
    if (window.fbAsyncInit) {
      console.log('fbAsyncInit already set, waiting for initialization...');
      // Wait a bit for initialization to complete
      setTimeout(() => {
        if (window.FB) {
          console.log('Facebook SDK initialized via existing fbAsyncInit');
          isSdkLoaded.value = true;
          emit('auth-initialized');
          resolve();
        } else {
          reject(new Error('Facebook SDK initialization timeout'));
        }
      }, 2000);
      return;
    }

    window.fbAsyncInit = () => {
      console.log('Facebook SDK initialized');
      window.FB.init({
        appId: props.appId,
        cookie: true,
        xfbml: true,
        version: props.version
      });

      isSdkLoaded.value = true;
      emit('auth-initialized');
      resolve();
    };

    (function(d, s, id){
      const fjs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)) { 
        console.log('Facebook SDK script already exists');
        return; 
      }
      const js = d.createElement(s);
      js.id = id;
      js.src = 'https://connect.facebook.net/en_US/sdk.js';
      js.onload = () => {
        console.log('Facebook SDK script loaded');
      };
      js.onerror = (error) => {
        console.error('Facebook SDK script load error:', error);
        sdkLoadError.value = 'Failed to load Facebook SDK';
        reject(error);
      };
      fjs.parentNode.insertBefore(js, fjs);
    })(document, 'script', 'facebook-jssdk');
  });
};

const login = async () => {
  console.log('Attempting Facebook login...');
  console.log('SDK loaded:', isSdkLoaded.value);
  console.log('Window FB:', !!window.FB);
  
  if (!isSdkLoaded.value || !window.FB) {
    throw new Error('Facebook SDK is not loaded');
  }

  const loginOptions = {
    scope: 'public_profile, email' // 필요한 권한 지정
  };
  
  try {
    return new Promise((resolve, reject) => {
      window.FB.login(function (response) {
        console.log('Facebook login response:', response);
        if (response.authResponse) {
          if (response.status === 'connected') {
            console.log('Login succeeded: ', response.authResponse.accessToken);
            resolve(response.authResponse.accessToken);
          } else {
            reject('Login failed: ' + response.status);
          }
        } else {
          reject('User cancelled login or did not fully authorize.');
        }
      }, loginOptions);
    });
  } catch (error) {
    console.error('Login failed: ', error);
    throw error;
  }
};

const logout = async () => {
  console.log('Attempting Facebook logout...');
  
  if (!isSdkLoaded.value || !window.FB) {
    throw new Error('Facebook SDK is not loaded');
  }

  const logoutPromise = () => {
    return new Promise((resolve) => {
      window.FB.getLoginStatus(function (response) {
        if (response && response.status === 'connected') {
          window.FB.logout(function (response) {
            console.log('Logout response:', response);
            resolve(response);
          });
        } else {
          resolve(response);
        }
      });
    });
  };
  await logoutPromise();
};

const getProfile = async () => {
  console.log('Getting Facebook profile...');
  
  if (!isSdkLoaded.value || !window.FB) {
    throw new Error('Facebook SDK is not loaded');
  }

  const profilePromise = () => {
    return new Promise((resolve, reject) => {
      window.FB.api('/me', {fields: 'name,email'}, function (response) {
        console.log('Profile response:', response);
        if (response && !response.error) {
          resolve(response);
        } else {
          reject('can\'t get profile: ' + (response.error ? response.error.message : 'unknown error'));
        }
      });
    });
  };
  return await profilePromise();
};

// 초기화 상태 확인 메서드
const isInitialized = () => {
  return isSdkLoaded.value && !!window.FB;
};

// Expose methods for parent components
defineExpose({
  login,
  logout,
  getProfile,
  isInitialized,
  isSdkLoaded,
  sdkLoadError
});

// Lifecycle
onMounted(async () => {
  console.log('FacebookAuth component mounted');
  console.log('Component props:', {
    appId: props.appId,
    version: props.version
  });
  
  try {
    await loadFacebookSDK();
  } catch (error) {
    console.error('Error loading Facebook SDK', error);
    sdkLoadError.value = error.message;
  }
});
</script>