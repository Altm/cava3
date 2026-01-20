import { createRouter, createWebHistory } from 'vue-router'
import ProductListView from '@/views/ProductListView.vue'
import ProductForm from '@/views/ProductForm.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'ProductList',
      component: ProductListView
    },
    {
      path: '/product-list',
      name: 'ProductListPage',
      component: ProductListView
    },
    {
      path: '/product-form',
      name: 'ProductForm',
      component: ProductForm
    },
    {
      path: '/product-form/:id',
      name: 'EditProduct',
      component: ProductForm,
      props: true
    }
  ],
})

export default router
