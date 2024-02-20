import Vue from 'vue';
import Router from 'vue-router';
import ExecResult from '../components/ExecResult';
import Problems from '../components/Problems';
import FeedManagement from '../components/FeedManagement';
import Search from '../components/Search';
import Login from '../components/Login';
import AuthCallback from '../components/AuthCallback';

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
        },
        {
            path: '/search',
            name: 'Search',
            component: Search
        },
        {
            path: '/login',
            name: 'Login',
            component: Login
        },
        {
            path: '/logout',
            name: 'Logout',
            component: Login
        },
        {
            path: '/auth-callback',
            name: 'AuthCallback',
            component: AuthCallback
        },
    ]
})
