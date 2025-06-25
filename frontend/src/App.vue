<template>
  <div id="app">
    <nav class="navbar navbar-expand-sm navbar-dark bg-secondary">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">FeedMaker</a>
        
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav-collapse" aria-controls="nav-collapse" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        
        <div class="collapse navbar-collapse" id="nav-collapse">
          <ul class="navbar-nav me-auto">
            <li class="nav-item">
              <router-link to="/result" class="nav-link">실행 결과</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/problems" class="nav-link">문제점과 상태</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/management" class="nav-link">피드 관리</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/search" class="nav-link">사이트 검색</router-link>
            </li>
          </ul>
          
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <router-link to="/login" class="nav-link">
                <font-awesome-icon :icon="['fa', 'user-circle']" />
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <router-view />
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

.nav-link {
  color: rgba(255, 255, 255, 0.75) !important;
  text-decoration: none !important;
  padding: 0.5rem 1rem !important;
}

.nav-link:hover {
  color: rgba(255, 255, 255, 1) !important;
}

.navbar-nav .nav-link {
  color: rgba(255, 255, 255, 0.75) !important;
}

.navbar-nav .nav-link:hover {
  color: rgba(255, 255, 255, 1) !important;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>

<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUserCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faUserCircle);
</script>
