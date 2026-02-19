<template>
  <div class="product-list-2-container">
    <!-- Header -->
    <div class="page-header">
      <div class="page-title">
        <h1>📦 Продукты 2</h1>
        <p class="page-subtitle">Управление продуктами с поддержкой дробных единиц и составных товаров</p>
      </div>
      <div class="header-actions">
        <button 
          v-if="hasPermission('product.write')" 
          @click="showCreateModal" 
          class="btn btn-primary btn-lg"
        >
          ➕ Создать продукт
        </button>
        <button @click="refreshData" class="btn btn-outline" :disabled="loading">
          🔄 Обновить
        </button>
      </div>
    </div>

    <!-- Filters Card -->
    <div class="filters-card">
      <div class="filters-grid">
        <!-- Search by Name -->
        <div class="filter-group">
          <label class="filter-label">🔍 Поиск по названию</label>
          <input
            v-model="filters.name"
            type="text"
            placeholder="Введите название..."
            list="product-name-suggestions"
            @input="onFilterInput"
            @keyup.enter="applyFilters"
            class="form-control"
          />
          <datalist id="product-name-suggestions">
            <option v-for="name in nameSuggestions" :key="name" :value="name" />
          </datalist>
        </div>

        <!-- Location Filter -->
        <div class="filter-group">
          <label class="filter-label">📍 Локация</label>
          <select v-model.number="filters.locationId" @change="applyFilters" class="form-control">
            <option :value="null">Все локации</option>
            <option v-for="loc in locations" :key="loc.id" :value="loc.id">
              {{ loc.name }} ({{ loc.code }})
            </option>
          </select>
        </div>

        <!-- Product Type Filter -->
        <div class="filter-group">
          <label class="filter-label">🏷️ Тип продукта</label>
          <select v-model.number="filters.productTypeId" @change="applyFilters" class="form-control">
            <option :value="null">Все типы</option>
            <option v-for="type in productTypes" :key="type.id" :value="type.id">
              {{ type.name }}
            </option>
          </select>
        </div>

        <!-- Composite Filter -->
        <div class="filter-group">
          <label class="filter-label">📊 Тип товара</label>
          <select v-model="filters.isComposite" @change="applyFilters" class="form-control">
            <option :value="null">Все</option>
            <option :value="true">Составные</option>
            <option :value="false">Простые</option>
          </select>
        </div>

        <!-- Unit Filter -->
        <div class="filter-group">
          <label class="filter-label">📏 Единица измерения</label>
          <select v-model.number="filters.unitId" @change="applyFilters" class="form-control">
            <option :value="null">Все единицы</option>
            <option v-for="unit in units" :key="unit.id" :value="unit.id">
              {{ unit.description }} ({{ unit.code }})
            </option>
          </select>
        </div>

        <!-- Filter Actions -->
        <div class="filter-group filter-actions-group">
          <label class="filter-label">&nbsp;</label>
          <div class="filter-buttons">
            <button @click="applyFilters" class="btn btn-primary">Применить</button>
            <button @click="resetFilters" class="btn btn-outline">Сброс</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Products Table -->
    <div class="table-card">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Загрузка продуктов...</p>
      </div>

      <div v-else-if="products.length === 0" class="empty-state">
        <div class="empty-icon">📦</div>
        <h3>Нет продуктов</h3>
        <p>Продукты не найдены по заданным фильтрам</p>
        <button @click="resetFilters" class="btn btn-primary">Сбросить фильтры</button>
      </div>

      <table v-else class="products-table">
        <thead>
          <tr>
            <th class="col-id">ID</th>
            <th class="col-name">Название</th>
            <th class="col-sku">SKU</th>
            <th class="col-type">Тип</th>
            <th class="col-units">Единицы</th>
            <th class="col-stock">Остаток</th>
            <th class="col-cost">Стоимость</th>
            <th class="col-composite">Составной</th>
            <th class="col-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in products" :key="product.id" class="product-row">
            <td class="col-id">{{ product.id }}</td>
            <td class="col-name">
              <div class="product-name-cell">
                <span class="product-name">{{ product.name }}</span>
                <span v-if="hasProductImage(product)" class="has-image-indicator" title="Есть фото">🖼️</span>
              </div>
            </td>
            <td class="col-sku">
              <span v-if="product.sku" class="sku-badge">{{ product.sku }}</span>
              <span v-else class="no-sku">—</span>
            </td>
            <td class="col-type">
              <span class="type-badge" :title="getProductTypeDescription(product.productTypeId)">
                {{ getProductTypeName(product.productTypeId) }}
              </span>
            </td>
            <td class="col-units">
              <div class="units-cell">
                <span class="base-unit-badge" :title="'Базовая единица: ID ' + product.baseUnitId">
                  📏
                </span>
                <span v-if="product.productUnits && product.productUnits.length > 1" class="fractional-units-count">
                  +{{ product.productUnits.length - 1 }} дробных
                </span>
              </div>
            </td>
            <td class="col-stock">
              <span class="stock-value" :class="{ 'low-stock': product.stock < 5 }">
                {{ formatNumber(product.stock) }}
              </span>
            </td>
            <td class="col-cost">{{ formatCurrency(product.baseCost) }}</td>
            <td class="col-composite">
              <span 
                class="composite-badge" 
                :class="product.isComposite ? 'composite-yes' : 'composite-no'"
              >
                {{ product.isComposite ? '✅ Да' : '❌ Нет' }}
              </span>
            </td>
            <td class="col-actions">
              <div class="action-buttons">
                <router-link
                  :to="`/products2/${product.id}`"
                  class="btn btn-sm btn-info"
                  title="Просмотр"
                >
                  👁️
                </router-link>
                <button
                  v-if="hasPermission('product.write')"
                  @click="showEditModal(product.id)"
                  class="btn btn-sm btn-primary"
                  title="Редактировать"
                >
                  ✏️
                </button>
                <button
                  v-if="hasPermission('product.delete')"
                  @click="confirmDelete(product.id)"
                  class="btn btn-sm btn-danger"
                  title="Удалить"
                  :disabled="product.isComposite && hasCompositeDependencies(product.id)"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && products.length > 0" class="pagination-card">
      <div class="pagination-info">
        Показано {{ products.length }} из {{ pagination.total }} продуктов
      </div>
      <div class="pagination-controls">
        <button
          @click="goToPage(pagination.currentPage - 1)"
          :disabled="pagination.currentPage <= 1"
          class="btn btn-outline"
        >
          ← Предыдущая
        </button>
        <span class="page-indicator">
          Страница {{ pagination.currentPage }} из {{ totalPages }}
        </span>
        <button
          @click="goToPage(pagination.currentPage + 1)"
          :disabled="pagination.currentPage >= totalPages"
          class="btn btn-outline"
        >
          Следующая →
        </button>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ editingProductId ? 'Редактировать продукт' : 'Создать продукт' }}</h2>
          <button @click="closeModal" class="btn-close">&times;</button>
        </div>
        <div class="modal-body">
          <ProductForm2
            :product-id="editingProductId"
            @close="closeModal"
            @saved="onProductSaved"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { 
  Product, 
  ProductType, 
  Unit, 
  Location,
  FilterState 
} from '@/api/productApi2'
import { productApi2, type Location as LocationType } from '@/api/productApi2'
import ProductForm2 from './ProductForm2.vue'

// Auth store
const authStore = useAuthStore()

// Permission check
const hasPermission = (permission: string): boolean => {
  return authStore.hasPermission(permission)
}

const hasProductImage = (product: Product): boolean => {
  // Check if product has image in meta (will be populated if needed)
  return false
}

// State
const products = ref<Product[]>([])
const productTypes = ref<ProductType[]>([])
const units = ref<Unit[]>([])
const locations = ref<LocationType[]>([])
const nameSuggestions = ref<string[]>([])
const loading = ref(true)
const showModal = ref(false)
const editingProductId = ref<number | null>(null)

// Filters
const filters = ref<FilterState>({
  locationId: null,
  productTypeId: null,
  name: '',
  isComposite: null,
  unitId: null,
})

// Pagination
const pagination = ref({
  currentPage: 1,
  pageSize: 50,
  total: 0,
})

// Computed
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))

// Methods
const formatNumber = (value: number): string => {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(value)
}

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(value)
}

const getProductTypeName = (productTypeId: number): string => {
  const productType = productTypes.value.find(pt => pt.id === productTypeId)
  return productType ? productType.name : 'Неизвестный тип'
}

const getProductTypeDescription = (productTypeId: number): string => {
  const productType = productTypes.value.find(pt => pt.id === productTypeId)
  return productType ? `${productType.name}${productType.description ? ': ' + productType.description : ''}` : ''
}

const hasCompositeDependencies = (productId: number): boolean => {
  // Check if this product is used as a component in other composite products
  // This is a simplified check - in real implementation, you'd query the backend
  return false
}

const loadProducts = async () => {
  try {
    loading.value = true
    const skip = (pagination.value.currentPage - 1) * pagination.value.pageSize

    products.value = await productApi2.getProducts({
      locationId: filters.value.locationId || undefined,
      productTypeId: filters.value.productTypeId || undefined,
      name: filters.value.name || undefined,
      skip,
      limit: pagination.value.pageSize,
    })

    pagination.value.total = await productApi2.getProductsCount({
      locationId: filters.value.locationId || undefined,
      productTypeId: filters.value.productTypeId || undefined,
      name: filters.value.name || undefined,
    })
  } catch (error) {
    console.error('Error loading products:', error)
    alert('Ошибка при загрузке продуктов')
  } finally {
    loading.value = false
  }
}

const loadReferenceData = async () => {
  try {
    const [types, unitsData, locationsData] = await Promise.all([
      productApi2.getProductTypes(),
      productApi2.getUnits(),
      productApi2.getLocations(),
    ])

    productTypes.value = types
    units.value = unitsData
    locations.value = locationsData
  } catch (error) {
    console.error('Error loading reference data:', error)
  }
}

const loadNameSuggestions = async () => {
  const query = filters.value.name.trim()
  if (!query) {
    nameSuggestions.value = []
    return
  }
  try {
    const rows = await productApi2.getProducts({
      name: query,
      limit: 10,
    })
    nameSuggestions.value = [...new Set(rows.map((product) => product.name))]
  } catch (error) {
    console.error('Error loading name suggestions:', error)
  }
}

const applyFilters = async () => {
  pagination.value.currentPage = 1
  await Promise.all([loadProducts(), loadNameSuggestions()])
}

const onFilterInput = async () => {
  await loadNameSuggestions()
}

const resetFilters = () => {
  filters.value = {
    locationId: null,
    productTypeId: null,
    name: '',
    isComposite: null,
    unitId: null,
  }
  pagination.value.currentPage = 1
  applyFilters()
}

const refreshData = async () => {
  await Promise.all([loadProducts(), loadReferenceData()])
}

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  pagination.value.currentPage = page
  loadProducts()
}

const showCreateModal = () => {
  editingProductId.value = null
  showModal.value = true
}

const showEditModal = (productId: number) => {
  editingProductId.value = productId
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingProductId.value = null
}

const onProductSaved = () => {
  closeModal()
  loadProducts()
}

const confirmDelete = async (productId: number) => {
  const product = products.value.find(p => p.id === productId)
  if (!product) return

  const confirmed = confirm(
    `Вы уверены, что хотите удалить продукт "${product.name}"?\n\nЭто действие нельзя отменить!`
  )
  
  if (!confirmed) return

  try {
    await productApi2.deleteProduct(productId)
    alert('Продукт удалён')
    loadProducts()
  } catch (error) {
    console.error('Error deleting product:', error)
    alert('Ошибка при удалении продукта')
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadReferenceData(),
    loadProducts(),
  ])
})
</script>

<style scoped>
.product-list-2-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background: #f8fafc;
  min-height: 100vh;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.page-title h1 {
  margin: 0 0 4px 0;
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  background: white;
  color: #475569;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-outline {
  background: white;
  color: #475569;
}

.btn-info {
  background: #06b6d4;
  color: white;
  border-color: #06b6d4;
}

.btn-danger {
  background: #ef4444;
  color: white;
  border-color: #ef4444;
}

.btn-lg {
  padding: 10px 20px;
  font-size: 15px;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

/* Filters Card */
.filters-card {
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.filter-group {
  display: flex;
  flex-direction: column;
}

.filter-actions-group {
  justify-content: flex-end;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 6px;
}

.form-control {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}

.form-control:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.filter-buttons {
  display: flex;
  gap: 8px;
}

/* Table Card */
.table-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.loading-state,
.empty-state {
  padding: 60px 20px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  color: #1e293b;
}

.empty-state p {
  margin: 0 0 16px 0;
  color: #64748b;
}

.products-table {
  width: 100%;
  border-collapse: collapse;
}

.products-table th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e2e8f0;
}

.products-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.product-row:hover {
  background: #f8fafc;
}

.col-id {
  width: 60px;
  color: #94a3b8;
  font-family: monospace;
}

.col-name {
  min-width: 200px;
}

.product-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.product-name {
  font-weight: 500;
  color: #1e293b;
}

.has-image-indicator {
  font-size: 12px;
}

.col-sku {
  width: 120px;
}

.sku-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #475569;
}

.no-sku {
  color: #cbd5e1;
}

.col-type {
  min-width: 150px;
}

.type-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.col-units {
  width: 120px;
}

.units-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.base-unit-badge {
  font-size: 16px;
}

.fractional-units-count {
  font-size: 12px;
  color: #64748b;
}

.col-stock {
  width: 100px;
  text-align: right;
}

.stock-value {
  font-weight: 600;
  color: #10b981;
}

.stock-value.low-stock {
  color: #f59e0b;
}

.col-cost {
  width: 100px;
  text-align: right;
  font-weight: 600;
  color: #1e293b;
}

.col-composite {
  width: 100px;
}

.composite-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.composite-yes {
  background: #dcfce7;
  color: #166534;
}

.composite-no {
  background: #f1f5f9;
  color: #64748b;
}

.col-actions {
  width: 120px;
}

.action-buttons {
  display: flex;
  gap: 6px;
}

/* Pagination */
.pagination-card {
  background: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-info {
  font-size: 14px;
  color: #64748b;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-indicator {
  font-size: 14px;
  color: #64748b;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 1000px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.btn-close {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #64748b;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-close:hover {
  background: #f1f5f9;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}
</style>
