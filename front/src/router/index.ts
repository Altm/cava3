import { createRouter, createWebHistory } from 'vue-router'
import ProductListView from '@/views/ProductListView.vue'
import ProductForm from '@/views/ProductForm.vue'
import SalesView from '@/views/SalesView.vue'
import ProductTypeManagement from '@/views/ProductTypeManagement.vue'

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
    },
    {
      path: '/product-types',
      name: 'ProductTypeManagement',
      component: ProductTypeManagement
    },
    {
      path: '/sales',
      name: 'Sales',
      component: SalesView
    }
  ],
})

export default router
