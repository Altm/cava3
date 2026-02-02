import { createRouter, createWebHistory } from 'vue-router'
import ProductListView from '@/views/ProductListView.vue'
import ProductForm from '@/views/ProductForm.vue'
import SalesView from '@/views/SalesView.vue'
import ProductTypeManagement from '@/views/ProductTypeManagement.vue'
import Login from '@/views/Login.vue'
import { isAuthenticated } from '@/api/authApi'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login
    },
    {
      path: '/',
      name: 'ProductList',
      component: ProductListView,
      meta: { requiresAuth: true }
    },
    {
      path: '/product-list',
      name: 'ProductListPage',
      component: ProductListView,
      meta: { requiresAuth: true }
    },
    {
      path: '/product-form',
      name: 'ProductForm',
      component: ProductForm,
      meta: { requiresAuth: true }
    },
    {
      path: '/product-form/:id',
      name: 'EditProduct',
      component: ProductForm,
      props: true,
      meta: { requiresAuth: true }
    },
    {
      path: '/product-types',
      name: 'ProductTypeManagement',
      component: ProductTypeManagement,
      meta: { requiresAuth: true }
    },
    {
      path: '/sales',
      name: 'Sales',
      component: SalesView,
      meta: { requiresAuth: true }
    },
    {
      path: '/units',
      name: 'UnitManagement',
      component: () => import('@/views/UnitManagement.vue'),
      meta: { requiresAuth: true }
    }
  ],
})

// Global navigation guard
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    // Redirect to login page if not authenticated
    next('/login')
  } else {
    next()
  }
})

export default router
