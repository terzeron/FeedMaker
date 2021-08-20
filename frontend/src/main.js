import Vue from 'vue'
import App from './App'
import router from './router';

import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-vue/dist/bootstrap-vue.css'

import { library } from '@fortawesome/fontawesome-svg-core'
import { faCaretDown, faCaretRight, faTrash, faPen, faList, faPlus, faMinus, faArrowDown } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

import JsonEditor from 'vue-json-edit';
import VueSimpleMarkdown from 'vue-simple-markdown';
import 'vue-simple-markdown/dist/vue-simple-markdown.css';

Vue.use(BootstrapVue);
Vue.use(IconsPlugin);
Vue.use(JsonEditor);
Vue.use(VueSimpleMarkdown);

library.add(faCaretDown, faCaretRight, faTrash, faPen, faList, faPlus, faMinus, faArrowDown);
Vue.component('font-awesome-icon', FontAwesomeIcon);

Vue.config.productionTip = false;

/* eslint-disable no-new */
new Vue({
    el: '#app',
    router,
    components: { App },
    template: '<App/>'
})
