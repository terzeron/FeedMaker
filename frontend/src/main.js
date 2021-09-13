import Vue from 'vue'
import App from './App'
import router from './router';

import { BootstrapVue } from 'bootstrap-vue';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-vue/dist/bootstrap-vue.css'
import VueSimpleMarkdown from 'vue-simple-markdown';
import 'vue-simple-markdown/dist/vue-simple-markdown.css';

Vue.use(VueSimpleMarkdown);
Vue.use(BootstrapVue);

Vue.config.productionTip = false;

/* eslint-disable no-new */
new Vue({
    el: '#app',
    router,
    render: h => h(App),
    components: { App },
    template: '<App/>'
})
