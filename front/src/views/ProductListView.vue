<template>
  <div class="product-list-container">
    <h2>Список товаров</h2>
    <div class="actions">
      <button v-if="hasPermission('product.write')" @click="showCreateProductModal" class="btn btn-primary">Создать товар</button>
      <router-link v-if="hasPermission('product_type.read')" to="/product-types" class="btn btn-secondary">Управление типами</router-link>
    </div>

    <!-- Filters -->
    <div class="filter-card">
      <form>
        <div class="form-group">
          <label>Локация:</label>
          <select
            v-model="filters.locationId"
            @change="loadProducts"
          >
            <option value="">Все локации</option>
            <option
              v-for="location in locations"
              :key="location.id"
              :value="location.id"
            >
              {{ location.name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Тип товара:</label>
          <select
            v-model="filters.productTypeId"
            @change="loadProducts"
          >
            <option value="">Все типы</option>
            <option
              v-for="type in productTypes"
              :key="type.id"
              :value="type.id"
            >
              {{ type.name }}
            </option>
          </select>
        </div>

        <button @click="resetFilters" type="button">Сбросить</button>
      </form>
    </div>

    <!-- Table -->
    <div v-if="loading">Загрузка...</div>
    <table v-else class="product-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Название</th>
          <th>Тип товара</th>
          <th>Основная единица</th>
          <th>Остаток</th>
          <th>Себестоимость</th>
          <th>Составной</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="product in products" :key="product.id">
          <td>{{ product.id }}</td>
          <td>{{ product.name }}</td>
          <td>{{ getProductTypeName(product.productTypeId) }}</td>
          <td>{{ getBaseUnit(product) }}</td>
          <td>{{ product.stock }}</td>
          <td>{{ product.unitCost }}</td>
          <td>
            <span :class="{'tag-success': product.isComposite, 'tag-info': !product.isComposite}">
              {{ product.isComposite ? 'Да' : 'Нет' }}
            </span>
          </td>
          <td>
            <button v-if="hasPermission('product.write')" @click="showEditProductModal(product.id)" class="btn btn-sm">Редактировать</button>
            <button v-if="hasPermission('product.delete')" @click="deleteProduct(product.id)" class="btn btn-sm btn-danger">Удалить</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination -->
    <div class="pagination" v-if="!loading">
      <div class="pagination-info">
        Показано {{ Math.min(pagination.pageSize, products.length) }} из {{ pagination.total }}
      </div>
      <div class="pagination-controls">
        <button
          @click="handleCurrentChange(pagination.currentPage - 1)"
          :disabled="pagination.currentPage <= 1"
        >
          Предыдущая
        </button>
        <span>{{ pagination.currentPage }} из {{ Math.ceil(pagination.total / pagination.pageSize) }}</span>
        <button
          @click="handleCurrentChange(pagination.currentPage + 1)"
          :disabled="pagination.currentPage >= Math.ceil(pagination.total / pagination.pageSize)"
        >
          Следующая
        </button>
      </div>
    </div>

    <!-- Product Form Modal -->
    <div v-if="showProductModal" class="modal-overlay" @click="closeProductModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingProductId ? 'Редактировать товар' : 'Создать товар' }}</h3>
          <button @click="closeProductModal" class="btn-close">&times;</button>
        </div>
        <div class="modal-body">
          <ProductForm
            :productId="editingProductId"
            @close="closeProductModal"
            @saved="onProductSaved"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Product, ProductType, Location } from '@/api/productApi'
import { productApi } from '@/api/productApi'
import ProductForm from './ProductForm.vue' // Импортируем компонент формы

// Auth store
const authStore = useAuthStore();

// Check permission function
const hasPermission = (permission: string): boolean => {
  return authStore.hasPermission(permission);
};

const router = useRouter()
const products = ref<Product[]>([])
const productTypes = ref<ProductType[]>([])
const locations = ref<Location[]>([])
const loading = ref(true)

// Modal state
const showProductModal = ref(false)
const editingProductId = ref<number | null>(null)

// Filters
const filters = ref({
  locationId: null as number | null,
  productTypeId: null as number | null,
})

// Pagination
const pagination = ref({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// Load products with pagination and filters
const loadProducts = async () => {
  try {
    loading.value = true

    // Calculate skip based on current page and page size
    const skip = (pagination.value.currentPage - 1) * pagination.value.pageSize

    // Load products with filters and pagination
    products.value = await productApi.getProducts({
      locationId: filters.value.locationId || undefined,
      productTypeId: filters.value.productTypeId || undefined,
      skip,
      limit: pagination.value.pageSize
    })

    // Load total count for pagination
    pagination.value.total = await productApi.getProductsCount({
      locationId: filters.value.locationId || undefined,
      productTypeId: filters.value.productTypeId || undefined
    })
  } catch (error) {
    console.error('Error loading products:', error)
  } finally {
    loading.value = false
  }
}

const loadProductTypes = async () => {
  try {
    productTypes.value = await productApi.getProductTypes()
  } catch (error) {
    console.error('Error loading product types:', error)
  }
}

const loadLocations = async () => {
  try {
    locations.value = await productApi.getLocations()
  } catch (error) {
    console.error('Error loading locations:', error)
  }
}

const getProductTypeName = (productTypeId: number) => {
  const productType = productTypes.value.find(pt => pt.id === productTypeId)
  return productType ? productType.name : 'Неизвестный тип'
}

const getBaseUnit = (product: Product) => {
  // In a real implementation, this would come from the product's base_unit_code
  // For now, we'll return a placeholder
  return 'шт'; // Default unit
}

const showCreateProductModal = () => {
  editingProductId.value = null
  showProductModal.value = true
}

const showEditProductModal = (productId: number) => {
  editingProductId.value = productId
  showProductModal.value = true
}

const closeProductModal = () => {
  showProductModal.value = false
  editingProductId.value = null
}

const onProductSaved = () => {
  closeProductModal()
  loadProducts() // Refresh the list after saving
}

const deleteProduct = async (productId: number) => {
  if (confirm('Вы уверены, что хотите удалить этот товар?')) {
    try {
      await productApi.deleteProduct(productId)
      await loadProducts() // Refresh the list
    } catch (error) {
      console.error('Error deleting product:', error)
      alert('Ошибка при удалении товара')
    }
  }
}

const resetFilters = () => {
  filters.value.locationId = null
  filters.value.productTypeId = null
  loadProducts()
}

const handleSizeChange = (val: number) => {
  pagination.value.pageSize = val
  loadProducts()
}

const handleCurrentChange = (val: number) => {
  pagination.value.currentPage = val
  loadProducts()
}

// Watch for filter changes and reload products
watch(filters, () => {
  // Reset to first page when filters change
  pagination.value.currentPage = 1
  loadProducts()
}, { deep: true })

onMounted(async () => {
  await Promise.all([
    loadProductTypes(),
    loadLocations(),
    loadProducts() // Load products after other data is loaded
  ])
})
</script>

<style scoped>
.product-list-container {
  padding: 20px;
}

.actions {
  margin-bottom: 20px;
}

.btn {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  background-color: #f5f5f5;
  margin-right: 10px;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.form-group {
  margin-right: 15px;
  display: inline-block;
}

.filter-card {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.product-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.product-table th,
.product-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.product-table th {
  background-color: #f2f2f2;
}

.tag-success {
  background-color: #28a745;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
}

.tag-info {
  background-color: #17a2b8;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination button {
  margin: 0 5px;
  padding: 6px 12px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 0;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
}

.modal-body {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
