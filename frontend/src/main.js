import { createApp } from 'vue';
import App from './App';
import router from './router';

// Bootstrap CSS 로드
import 'bootstrap/dist/css/bootstrap.css';
import "bootstrap/dist/js/bootstrap.bundle.min.js";

// BootstrapVueNext CSS import
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css';

// vue-toastification
import Toast from "vue-toastification";
import "vue-toastification/dist/index.css";

// BootstrapVueNext 개별 컴포넌트 import
import {
  BButton,
  BAlert,
  BCard,
  BCardText,
  BTable,
  BProgress,
  BContainer,
  BRow,
  BCol,
  BForm,
  BFormGroup,
  BFormInput,
  BFormSelect,
  BFormCheckbox,
  BFormRadio,
  BModal,
  BNav,
  BNavItem,
  BTableSimple,
  BThead,
  BTbody,
  BTr,
  BTh,
  BTd,
  BProgressBar,
  BInputGroup,
  BInputGroupText,
  BCardHeader,
  BCardBody,
  BSpinner,
} from 'bootstrap-vue-next';

import { VMarkdownView } from 'vue3-markdown';
import 'vue3-markdown/dist/vue3-markdown.css';

// Custom session utility
import session from './utils/session';

const app = createApp(App);

// BootstrapVueNext 플러그인 등록
// app.use(ToastPlugin);

// BootstrapVueNext 컴포넌트들을 개별적으로 등록
app.component('BButton', BButton);
app.component('BAlert', BAlert);
app.component('BCard', BCard);
app.component('BCardText', BCardText);
app.component('BTable', BTable);
app.component('BProgress', BProgress);
app.component('BContainer', BContainer);
app.component('BRow', BRow);
app.component('BCol', BCol);
app.component('BForm', BForm);
app.component('BFormGroup', BFormGroup);
app.component('BFormInput', BFormInput);
app.component('BFormSelect', BFormSelect);
app.component('BFormCheckbox', BFormCheckbox);
app.component('BFormRadio', BFormRadio);
app.component('BModal', BModal);
app.component('BNav', BNav);
app.component('BNavItem', BNavItem);
app.component('BTableSimple', BTableSimple);
app.component('BThead', BThead);
app.component('BTbody', BTbody);
app.component('BTr', BTr);
app.component('BTh', BTh);
app.component('BTd', BTd);
app.component('BProgressBar', BProgressBar);
app.component('BInputGroup', BInputGroup);
app.component('BInputGroupText', BInputGroupText);
app.component('BCardHeader', BCardHeader);
app.component('BCardBody', BCardBody);
app.component('BSpinner', BSpinner);

app.component('VMarkdownView', VMarkdownView);
app.use(router);

// Add session as global property
app.config.globalProperties.$session = session;

app.use(Toast, {
  transition: "Vue-Toastification__bounce",
  maxToasts: 20,
  newestOnTop: true
});

app.mount('#app');
