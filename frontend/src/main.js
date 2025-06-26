import { createApp } from 'vue';
import App from './App';
import router from './router';

// Bootstrap CSS 로드
import 'bootstrap/dist/css/bootstrap.css';

// BootstrapVueNext CSS import
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css';

// BootstrapVueNext 플러그인 import
import { createBootstrap } from 'bootstrap-vue-next';

import { VMarkdownView } from 'vue3-markdown';
import 'vue3-markdown/dist/vue3-markdown.css';

// Custom session utility
import session from './utils/session';

const app = createApp(App);

// BootstrapVueNext 플러그인 등록
app.use(createBootstrap());

app.component('VMarkdownView', VMarkdownView);
app.use(router);

// Add session as global property
app.config.globalProperties.$session = session;

app.mount('#app');
