<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar align="left">
        <q-btn
          flat
          dense
          round
          inset="true"
          icon="menu"
          aria-label="Menu"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title shrink="true">
          <q-icon name="home"></q-icon>
          FeedMakerWeb
        </q-toolbar-title>

        <q-tabs inline-label>
          <q-route-tab
            icon="history"
            to="/result"
            exact
          >
            실행 결과
          </q-route-tab>
          <q-route-tab
            icon="report_problem"
            to="/problems"
            exact
          >
            문제점
          </q-route-tab>
          <q-route-tab
            icon="build"
            to="/management"
            exact
          >
            피드 관리
          </q-route-tab>
        </q-tabs>

         <div>v{{ $q.version }}</div>
      </q-toolbar>

    </q-header>

    <q-page-container>
      <router-view/>
    </q-page-container>
  </q-layout>
</template>

<script lang="ts">

import {Vue, Options} from 'vue-class-component'

@Options({
  components: {}
})
export default class MainLayout extends Vue {
  leftDrawerOpen = false;

  toggleLeftDrawer() {
    this.leftDrawerOpen = !this.leftDrawerOpen
  }
}
</script>
