<template>
    <div id="app">
        <b-navbar type="dark" variant="secondary">
            <b-navbar-brand>FeedMaker</b-navbar-brand>
            <b-collapse is-nav>
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
                </b-navbar-nav>
            </b-collapse>
        </b-navbar>
        <div>
            <router-view/>
        </div>
    </div>
</template>

<style>
 .navbar-brand { margin-left: 10px; }
 .navbar-text { font-weight: bold; }
 a.navbar-link { text-decoration: none !important; }
 a.navbar-link > a { text-decoration: none !important; }
 a:-webkit-any-link { text-decoration: none !important; }
</style>

<script>
export default {
  name: 'App'
}
</script>

<style>
 #app {
     -webkit-font-smoothing: antialiased;
     -moz-osx-font-smoothing: grayscale;
     /*color: #2c3e50;*/
 }
</style>
