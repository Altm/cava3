import { createRouter, createWebHistory } from 'vue-router'
import ProductForm from '@/views/ProductForm.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/Home.vue')
    },
    {
      path: '/product-form',
      name: 'product-form',
      component: ProductForm
    }
  ],
})

export default router
