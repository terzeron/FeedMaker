import Vue from 'vue'
import Router from 'vue-router'
import ExecResult from '@/components/ExecResult';
import Problems from '@/components/Problems';
import FeedManagement from '@/components/FeedManagement';

Vue.use(Router);

export default new Router({
    mode: 'history',
    base: process.env.BASE_URL,
    routes: [
        {
            path: '/',
            name: 'Home',
            component: ExecResult
        },
        {
            path: '/result',
            name: 'ExecResult',
            component: ExecResult
        },
        {
            path: '/problems',
            name: 'Problems',
            component: Problems
        },
        {
            path: '/management',
            name: 'FeedManagement',
            component: FeedManagement,
            children: [
                {
                    path: ':group/:feed',
                    component: FeedManagement
                }
            ]
        }
    ]
})
