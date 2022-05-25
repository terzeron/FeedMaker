<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12">
        <div id="facebookAuthDemo">
          <div>
            <FacebookAuth @authInitialized="authInitialized" ref="authRef"/>
            <div>
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
    login: async function () {
      this.accessToken = await this.$refs.authRef.login();
      if (this.accessToken) {
        this.$session.set('access_token', this.accessToken);
        console.log("logged in");
      }

      this.profile = await this.$refs.authRef.getProfile();
      if (this.profile && this.profile['name']) {
        this.$session.set('name', this.profile['name']);
      }
      if (this.profile && this.profile['email'] == process.env.VUE_APP_ADMIN_EMAIL) {
        this.$session.set('is_authorized', true);
        console.log("authorized as " + this.profile['name'] + ' (' + this.profile['email'] + ')');
      }

      await this.$router.push('/result');
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
    console.log(process.env);
  },
};
</script>
