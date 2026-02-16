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
      props: (route) => ({ productId: Number(route.params.id) }),
      meta: { requiresAuth: true }
    },
    {
      path: '/product-view/:id',
      name: 'ProductView',
      component: () => import('@/views/ProductView.vue'),
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
    },
    {
      path: '/serial/receipts',
      name: 'SerialReceipts',
      component: () => import('@/views/SerialReceiptsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/transfers',
      name: 'SerialTransfers',
      component: () => import('@/views/SerialTransfersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/inventories',
      name: 'SerialInventories',
      component: () => import('@/views/SerialInventoriesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/scan',
      name: 'SerialScan',
      component: () => import('@/views/SerialScanView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/receipts/list',
      name: 'SerialReceiptsList',
      component: () => import('@/views/SerialReceiptsListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/transfers/list',
      name: 'SerialTransfersList',
      component: () => import('@/views/SerialTransfersListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/inventories/list',
      name: 'SerialInventoriesList',
      component: () => import('@/views/SerialInventoriesListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/scan/boxes',
      name: 'SerialBoxesList',
      component: () => import('@/views/SerialBoxesListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/scan/items',
      name: 'SerialItemsList',
      component: () => import('@/views/SerialItemsListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/boxes/manage',
      name: 'SerialBoxesManage',
      component: () => import('@/views/SerialBoxesManageView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/receipts/edit/:id',
      name: 'SerialReceiptEdit',
      component: () => import('@/views/SerialReceiptEditView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/receipts/view/:id',
      name: 'SerialReceiptView',
      component: () => import('@/views/SerialReceiptViewView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/transfers/edit/:id',
      name: 'SerialTransferEdit',
      component: () => import('@/views/SerialTransferEditView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/transfers/view/:id',
      name: 'SerialTransferView',
      component: () => import('@/views/SerialTransferViewView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/inventories/edit/:id',
      name: 'SerialInventoryEdit',
      component: () => import('@/views/SerialInventoryEditView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/serial/items/history/:id',
      name: 'SerialItemHistory',
      component: () => import('@/views/SerialItemHistoryView.vue'),
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
