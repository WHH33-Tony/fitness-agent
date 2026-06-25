import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import AdminView from '../views/admin/AdminView.vue'
import DashboardView from '../views/user/DashboardView.vue'
import ExerciseView from '../views/user/ExerciseView.vue'
import GuestView from '../views/guest/GuestView.vue'
import MovementsView from '../views/user/MovementsView.vue'
import PoseView from '../views/user/PoseView.vue'
import ProfileView from '../views/user/ProfileView.vue'
import QAView from '../views/user/QAView.vue'
import FeedbackView from '../views/user/FeedbackView.vue'
import NutritionView from '../views/user/NutritionView.vue'

// Electron 通过 file:// 加载时 History API 会抛 DOMException，需使用 hash 模式
const isFileProtocol = typeof window !== 'undefined' && window.location?.protocol === 'file:'

const router = createRouter({
  history: isFileProtocol ? createWebHashHistory() : createWebHistory(),
  routes: [
    { path: '/', component: GuestView },
    { path: '/guest', redirect: '/' },
    { path: '/auth', redirect: '/' },
    { path: '/dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/pose', component: PoseView, meta: { requiresAuth: true } },
    { path: '/qa', component: QAView, meta: { requiresAuth: true } },
    { path: '/exercise', component: ExerciseView, meta: { requiresAuth: true } },
    { path: '/nutrition', component: NutritionView, meta: { requiresAuth: true } },
    { path: '/movements', component: MovementsView, meta: { requiresAuth: true } },
    { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/feedback', component: FeedbackView, meta: { requiresAuth: true } },
    { path: '/admin', component: AdminView, meta: { requiresAuth: true, role: 'admin' } }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/'
  }
  if (to.meta.role && auth.role !== to.meta.role) {
    return '/dashboard'
  }
})

export default router
