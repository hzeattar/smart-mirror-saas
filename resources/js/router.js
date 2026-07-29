import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from './pages/LoginPage.vue'
import DashboardPage from './pages/DashboardPage.vue'
import ProductManagementPage from './pages/ProductManagementPage.vue'
import OrderTrackingDashboard from './pages/OrderTrackingDashboard.vue'
import MirrorsPage from './pages/MirrorsPage.vue'
import CheckoutPage from './pages/CheckoutPage.vue'
import TryOnJobsPage from './pages/TryOnJobsPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage, meta: { guest: true } },
    { path: '/checkout/:token', component: CheckoutPage, meta: { public: true } },
    { path: '/', component: DashboardPage },
    { path: '/products', component: ProductManagementPage },
    { path: '/orders', component: OrderTrackingDashboard },
    { path: '/try-on-jobs', component: TryOnJobsPage },
    { path: '/mirrors', component: MirrorsPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const hasToken = Boolean(localStorage.getItem('smart_mirror_token'))
  if (to.meta.public) return true
  if (!hasToken && !to.meta.guest) return '/login'
  if (hasToken && to.meta.guest) return '/'
  return true
})

export default router
