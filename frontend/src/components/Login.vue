<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12">
        <div id="facebookAuthView">
          <div>
            <FacebookAuth @auth-initialized="authInitialized" ref="authRef"/>
            <div>
              <div>initialized={{initialized}}, accessToken={{accessToken}}, status={{status}}, profile={{profile}}</div>
              <div v-if="name">
                <p>{{ name }}님으로 로그인하였습니다.</p>
              </div>
              <b-button variant="outline-primary" v-if="is_logged" href="#" v-on:click="logout()">
                Log out from Facebook
                <font-awesome-icon :icon="['fab', 'facebook']"/>
              </b-button>
              <b-button variant="outline-primary" v-else href="#" v-on:click="login">
                Log in to Facebook
                <font-awesome-icon :icon="['fab', 'facebook']"/>
              </b-button>
            </div>
          </div>
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
</style>

<script>
import FacebookAuth from "./FacebookAuth.vue";
import {library} from '@fortawesome/fontawesome-svg-core';
import {faFacebook} from '@fortawesome/free-brands-svg-icons';
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome';

library.add(faFacebook);

export default {
  name: 'Login',
  components: {
    FacebookAuth,
    FontAwesomeIcon,
  },
  data: function () {
    return {
      initialized: false,
      accessToken: null,
      status: null,
      profile: null,
    };
  },
  computed: {
    is_logged: function () {
      return this.$session.get('access_token') != undefined;
    },
    name: function () {
      return this.$session.get('name');
    }
  },
  methods: {
    authInitialized: function () {
      this.initialized = true;
    },
    safeSplit: function(str, delimiter) {
      if (str && str.includes(delimiter)) {
        return str.split(delimiter);
      }
      return [str];
    },
    login: async function () {
      if (this.$session.get('is_authorized')) {
        await this.$router.push('/result');
        return;
      }

      if (this.initialized) {
        this.accessToken = await this.$refs.authRef.login();
        if (this.accessToken) {
          this.$session.set('access_token', this.accessToken);
          console.log("logged in");
        }

        this.profile = await this.$refs.authRef.getProfile();
        if (this.profile && this.profile['name']) {
          this.profile = this.$session.profile;
          this.$session.set('name', this.profile['name']);
        }
        const loginAllowedEmailList = this.safeSplit(process.env.VUE_APP_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST, ",");
        if (this.profile && loginAllowedEmailList.includes(this.profile['email'])) {
          this.$session.set('is_authorized', true);
          console.log("authorized as " + this.profile['name'] + ' (' + this.profile['email'] + ')');
        }

        await this.$router.push('/result');
      } else {
        console.error('Facebook Auth is not initialized.');
      }
    },
    logout: async function () {
      this.$session.set('access_token', undefined);
      this.$session.set('is_authorized', false);
      this.$session.set('name', undefined);
      this.accessToken = null;

      this.$refs.authRef.logout();

      await this.$router.push('/result');
    },
  },
  mounted: function () {
    console.log(this.$session.getAll());
  },
};
</script>
