import Vue from 'vue';
import App from './App';
import router from './router';
import VueSession from 'vue-session';
import dotenv from 'dotenv';

import { BootstrapVue } from 'bootstrap-vue';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';
import VueSimpleMarkdown from 'vue-simple-markdown';
import 'vue-simple-markdown/dist/vue-simple-markdown.css';

dotenv.config();

Vue.use(VueSession, {persist: true});
Vue.use(BootstrapVue);
Vue.use(VueSimpleMarkdown);

Vue.config.productionTip = false;

/* eslint-disable no-new */
new Vue({
    el: '#app',
    router,
    render: h => h(App),
    components: { App },
    template: '<App/>'
})
