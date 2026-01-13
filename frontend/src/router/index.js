import { createRouter, createWebHistory } from 'vue-router';
import axios from 'axios';
import ExecResult from '@/components/ExecResult.vue';
import Problems from '@/components/Problems.vue';
import FeedManagement from '@/components/FeedManagement.vue';
import Search from '@/components/Search.vue';
import Login from '@/components/Login.vue';
import AuthCallback from '../components/AuthCallback';
import { getApiUrlPath } from '../utils/api';

const routes = [
    {
        path: '/',
        redirect: '/result'
    },
    {
        path: '/result',
        name: 'ExecResult',
        component: ExecResult,
        meta: { requiresAuth: true }
    },
    {
        path: '/problems',
        name: 'Problems',
        component: Problems,
        meta: { requiresAuth: true }
    },
    {
        path: '/management',
        name: 'FeedManagement',
        component: FeedManagement,
        meta: { requiresAuth: true }
    },
    {
        path: '/management/:group/:feed',
        name: 'FeedManagementWithParams',
        component: FeedManagement,
        props: true,
        meta: { requiresAuth: true }
    },
    {
        path: '/search',
        name: 'Search',
        component: Search,
        meta: { requiresAuth: true }
    },
    {
        path: '/login',
        name: 'Login',
        component: Login,
        meta: { requiresAuth: false }
    },
    {
        path: '/logout',
        name: 'Logout',
        component: Login,
        meta: { requiresAuth: false }
    },
    {
        path: '/auth-callback',
        name: 'AuthCallback',
        component: AuthCallback,
        meta: { requiresAuth: false }
    },
];

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL),
    routes
});

// 서버에서 인증 상태 확인 (httpOnly 쿠키 기반)
const checkAuthStatus = async () => {
    try {
        const response = await axios.get(
            `${getApiUrlPath()}/auth/me`,
            {
                withCredentials: true  // httpOnly 쿠키 포함
            }
        );
        return response.data.is_authenticated === true;
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
};

router.beforeEach(async (to, from, next) => {
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth);

    if (requiresAuth) {
        // 서버에 인증 상태 확인 (클라이언트 검증 우회 방지)
        const isAuthenticated = await checkAuthStatus();

        if (isAuthenticated) {
            next();
        } else {
            console.warn(`Unauthorized access attempt to ${to.path}`);

            // 기존 localStorage 데이터 정리 (보안 취약점 제거)
            localStorage.removeItem('is_authorized');
            localStorage.removeItem('access_token');
            localStorage.removeItem('name');
            localStorage.removeItem('session_expiry');

            next({
                path: '/login',
                query: { redirect: to.fullPath }
            });
        }
    } else {
        next();
    }
});

export default router;
