import { createRouter, createWebHistory } from 'vue-router';
import ExecResult from '@/components/ExecResult.vue';
import Problems from '@/components/Problems.vue';
import FeedManagement from '@/components/FeedManagement.vue';
import Search from '@/components/Search.vue';
import Login from '@/components/Login.vue';
import AuthCallback from '../components/AuthCallback';

const routes = [
    {
        path: '/',
        redirect: '/result'
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
        component: FeedManagement
    },
    {
        path: '/management/:group/:feed',
        name: 'FeedManagementWithParams',
        component: FeedManagement,
        props: true
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
];

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL),
    routes
});

export default router;
