import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Pos from '../views/Pos.vue'
import Inventory from '../views/Inventory.vue'
import Members from '../views/Members.vue'
import Reports from '../views/Reports.vue'
import Products from '../views/Products.vue'
import StoreManagement from '../views/StoreManagement.vue'
import Purchase from '../views/Purchase.vue'
import Login from '../views/Login.vue'
import { isAuthenticated, isOwner } from '../store/auth'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: Login, meta: { title: '登录', public: true } },
  { path: '/dashboard', name: 'dashboard', component: Dashboard, meta: { title: '今日概览' } },
  { path: '/pos', name: 'pos', component: Pos, meta: { title: '收银台' } },
  { path: '/inventory', name: 'inventory', component: Inventory, meta: { title: '库存管理' } },
  { path: '/products', name: 'products', component: Products, meta: { title: '商品管理', ownerOnly: true } },
  { path: '/stores', name: 'stores', component: StoreManagement, meta: { title: '门店管理', ownerOnly: true } },
  { path: '/members', name: 'members', component: Members, meta: { title: '会员管理' } },
  { path: '/purchase', name: 'purchase', component: Purchase, meta: { title: '进货管理' } },
  { path: '/reports', name: 'reports', component: Reports, meta: { title: '销售报表' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.public && !isAuthenticated()) {
    return '/login'
  }
  if (to.meta.public && isAuthenticated() && to.path === '/login') {
    return '/dashboard'
  }
  if (to.meta.ownerOnly && !isOwner()) {
    return '/dashboard'
  }
  return true
})

export default router
