<template>
  <div id="app">
    <b-navbar type="dark" variant="secondary" toggleable="sm">
      <b-navbar-brand href="#">FeedMaker</b-navbar-brand>

      <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>

      <b-collapse id="nav-collapse" is-nav>
        <b-navbar-nav>
          <b-nav-item>
            <router-link to="/result">
              <b-nav-text>실행 결과</b-nav-text>
            </router-link>
          </b-nav-item>
          <b-nav-item>
            <router-link to="/problems">
              <b-nav-text>문제점과 상태</b-nav-text>
            </router-link>
          </b-nav-item>
          <b-nav-item>
            <router-link to="/management">
              <b-nav-text>피드 관리</b-nav-text>
            </router-link>
          </b-nav-item>
          <b-nav-item>
            <router-link to="/search">
              <b-nav-text>사이트 검색</b-nav-text>
            </router-link>
          </b-nav-item>
        </b-navbar-nav>

        <b-navbar-nav class="ml-auto">
          <b-nav-item>
            <router-link to="/login">
              <b-nav-text>
                <font-awesome-icon :icon="['fa', 'user-circle']"/>
              </b-nav-text>
            </router-link>
          </b-nav-item>
        </b-navbar-nav>
      </b-collapse>
    </b-navbar>

    <router-view/>
  </div>
</template>

<style>
html {
  font-size: 14px;
}

.navbar-brand {
  margin-left: 10px;
}

.navbar-text {
  font-weight: bold;
}

a.navbar-link {
  text-decoration: none !important;
}

a.navbar-link > a {
  text-decoration: none !important;
}

a:-webkit-any-link {
  text-decoration: none !important;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /*color: #2c3e50;*/
}
</style>

<script>
import {library} from '@fortawesome/fontawesome-svg-core';
import {faUserCircle} from '@fortawesome/free-solid-svg-icons';
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome';

library.add(faUserCircle);

export default {
  name: 'App',
  components: {
    FontAwesomeIcon,
  },
};
</script>
