<template>
  <div class="product-view-2-container">
    <!-- Header with Navigation -->
    <div class="view-header">
      <div class="breadcrumb">
        <router-link to="/products2" class="breadcrumb-link">📦 Продукты 2</router-link>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">{{ product?.name || 'Загрузка...' }}</span>
      </div>
      <div class="header-actions">
        <button @click="goBack" class="btn btn-outline">← Назад</button>
        <button 
          v-if="hasPermission('product.write')" 
          @click="editProduct" 
          class="btn btn-primary"
        >
          ✏️ Редактировать
        </button>
        <a 
          :href="`/products2/${productId}/print`" 
          target="_blank" 
          class="btn btn-outline"
        >
          🖨️ Печать
        </a>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Загрузка информации о продукте...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Ошибка загрузки</h3>
      <p>{{ error }}</p>
      <button @click="loadProduct" class="btn btn-primary">Попробовать снова</button>
    </div>

    <!-- Product Content -->
    <div v-else-if="product" class="product-content">
      <!-- Main Info Card -->
      <div class="info-grid">
        <!-- Product Image & Basic Info -->
        <div class="card product-main-card">
          <div class="product-image-section">
            <div v-if="productImage" class="image-container">
              <img :src="productImage" :alt="product.name" class="product-image" />
            </div>
            <div v-else class="no-image">
              <span class="no-image-icon">📦</span>
              <p>Нет изображения</p>
            </div>
          </div>
          
          <div class="product-basic-info">
            <div class="product-header">
              <h1 class="product-title">{{ product.name }}</h1>
              <span v-if="product.sku" class="sku-badge">{{ product.sku }}</span>
            </div>
            
            <div class="info-row">
              <span class="info-label">Тип продукта:</span>
              <span class="info-value">
                <span class="type-badge">{{ getProductTypeName(product.productTypeId) }}</span>
              </span>
            </div>
            
            <div class="info-row">
              <span class="info-label">Составной:</span>
              <span class="info-value">
                <span 
                  class="composite-badge" 
                  :class="product.isComposite ? 'composite-yes' : 'composite-no'"
                >
                  {{ product.isComposite ? '✅ Да' : '❌ Нет' }}
                </span>
              </span>
            </div>
            
            <div class="info-row">
              <span class="info-label">Базовая стоимость:</span>
              <span class="info-value price-value">{{ formatCurrency(product.baseCost) }}</span>
            </div>
            
            <div class="info-row">
              <span class="info-label">Остаток:</span>
              <span class="info-value stock-value" :class="{ 'low-stock': product.stock < 5 }">
                {{ formatNumber(product.stock) }}
              </span>
            </div>
            
            <div class="info-row">
              <span class="info-label">Базовая единица:</span>
              <span class="info-value">{{ getBaseUnitLabel() }}</span>
            </div>
          </div>
        </div>

        <!-- Attributes Card -->
        <div v-if="productAttributes.length > 0" class="card attributes-card">
          <h3 class="card-title">🏷️ Атрибуты</h3>
          <div class="attributes-list">
            <div v-for="attr in productAttributes" :key="attr.id" class="attribute-row">
              <span class="attribute-name">{{ attr.name }}</span>
              <span class="attribute-value">{{ formatAttributeValue(attr) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Fractional Units Card -->
      <div class="card fractional-units-card">
        <div class="card-header-with-action">
          <h3 class="card-title">📏 Дробные единицы измерения</h3>
          <router-link 
            :to="`/products2/${productId}/edit`" 
            class="btn btn-sm btn-outline"
            v-if="hasPermission('product.write')"
          >
            ✏️ Редактировать
          </router-link>
        </div>
        
        <div v-if="fractionalUnits.length === 0" class="empty-state-small">
          <p>Дополнительные единицы измерения не настроены</p>
        </div>
        
        <div v-else class="units-table-wrapper">
          <table class="units-table">
            <thead>
              <tr>
                <th>Единица</th>
                <th>Код</th>
                <th>Тип</th>
                <th>Ratio к базовой</th>
                <th>Дискретный шаг</th>
                <th>Цена за единицу</th>
                <th>Продаж в базовой</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="unit in fractionalUnits" :key="unit.id" class="unit-row">
                <td>
                  <span class="unit-name-cell">
                    <span v-if="unit.isBase" class="base-unit-indicator">📏</span>
                    {{ unit.unitDescription }}
                  </span>
                </td>
                <td><code class="unit-code">{{ unit.unitCode }}</code></td>
                <td>
                  <span class="unit-type-badge" :class="'type-' + String(unit.unitType || '')">
                    {{ getUnitTypeName(unit.unitType || 'base') }}
                  </span>
                </td>
                <td class="ratio-value">{{ unit.ratioToBase }}</td>
                <td>{{ unit.discreteStep || '—' }}</td>
                <td class="price-value">
                  {{ formatCurrency(calculateUnitPrice(unit.ratioToBase)) }}
                </td>
                <td class="sales-count">
                  {{ calculateUnitsInBase(unit.ratioToBase) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Component Tree Card (for composite products) -->
      <div v-if="product.isComposite && componentTree.length > 0" class="card components-card">
        <h3 class="card-title">📦 Дерево компонентов</h3>
        <p class="card-subtitle">
          Рекурсивная структура всех компонентов продукта с текущей доступностью
        </p>
        
        <div class="component-tree">
          <ComponentTreeNode 
            v-for="(node, index) in componentTree" 
            :key="index"
            :node="node" 
            :level="0"
            :product-id="productId"
          />
        </div>
      </div>

      <!-- Components List Card -->
      <div v-if="product.components.length > 0" class="card components-list-card">
        <h3 class="card-title">🔗 Непосредственные компоненты</h3>
        <div class="components-grid">
          <div 
            v-for="component in product.components" 
            :key="component.id" 
            class="component-card"
          >
            <div class="component-card-header">
              <span class="component-name">{{ component.ingredientName || `Ингредиент #${component.ingredientId}` }}</span>
              <span class="component-sku">
                #{{ component.ingredientId }}
              </span>
            </div>
            <div class="component-card-body">
              <div class="component-stat">
                <span class="stat-label">Количество:</span>
                <span class="stat-value">{{ component.quantity }}</span>
              </div>
              <div class="component-stat">
                <span class="stat-label">Единица:</span>
                <span class="stat-value">{{ component.unitCode || '—' }}</span>
              </div>
              <div class="component-stat">
                <span class="stat-label">Замены:</span>
                <span class="stat-value" :class="component.substitutionAllowed ? 'allowed' : 'not-allowed'">
                  {{ component.substitutionAllowed ? '✅ Разрешены' : '❌ Запрещены' }}
                </span>
              </div>
            </div>
            <div class="component-card-footer">
              <span class="muted">Привязанный продукт выбирается через bindings ингредиента</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Usage Examples Card -->
      <div v-if="usageExamples.length > 0" class="card usage-examples-card">
        <h3 class="card-title">💡 Примеры использования</h3>
        <div class="examples-grid">
          <div v-for="(example, index) in usageExamples" :key="index" class="example-card">
            <div class="example-card-icon">
              {{ getExampleIcon(example.type) }}
            </div>
            <div class="example-card-content">
              <h4 class="example-card-title">{{ example.title }}</h4>
              <p class="example-card-description">{{ example.description }}</p>
              <div v-if="example.ratio" class="example-card-ratio">
                <code>{{ example.ratio }}</code> к базовой
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Stock by Location Card -->
      <div v-if="product.stockByLocation && product.stockByLocation.length > 0" class="card stock-card">
        <h3 class="card-title">📍 Остатки по локациям</h3>
        <div class="stock-table-wrapper">
          <table class="stock-table">
            <thead>
              <tr>
                <th>Локация</th>
                <th>Код</th>
                <th>Базовое количество</th>
                <th>Отображаемое</th>
                <th>Единицы</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="location in product.stockByLocation" :key="location.locationId">
                <td>{{ location.locationName }}</td>
                <td><code>{{ location.locationCode }}</code></td>
                <td class="stock-value">{{ formatNumber(location.baseQuantity) }}</td>
                <td>{{ location.displayQuantity }}</td>
                <td>
                  <div class="stock-units">
                    <span 
                      v-for="unit in location.units" 
                      :key="unit.unitId" 
                      class="stock-unit-badge"
                    >
                      {{ unit.unitCode }}: {{ formatNumber(unit.quantity) }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { 
  ProductView, 
  ProductUnit, 
  ProductAttributeDefinition,
  ProductComponentTreeNode,
  ProductUsageExample,
  ProductType,
  Unit as UnitType,
} from '@/api/productApi2'
import { productApi2 } from '@/api/productApi2'
import ComponentTreeNode from './ComponentTreeNode.vue'

// Auth store
const authStore = useAuthStore()

// Permission check
const hasPermission = (permission: string): boolean => {
  return authStore.hasPermission(permission)
}

// Route and Router
const route = useRoute()
const router = useRouter()
const productId = computed(() => Number(route.params.id))

// State
const loading = ref(true)
const error = ref<string | null>(null)
const product = ref<ProductView | null>(null)
const fractionalUnits = ref<ProductUnit[]>([])
const componentTree = ref<ProductComponentTreeNode[]>([])
const usageExamples = ref<ProductUsageExample[]>([])
const productTypes = ref<ProductType[]>([])
const units = ref<UnitType[]>([])

// Computed
const productImage = computed(() => {
  const raw = product.value?.meta?.image?.trim()
  if (!raw) return ''
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw
  const normalized = raw
    .replace(/^\/app\/public\/images\//, '')
    .replace(/^app\/public\/images\//, '')
    .replace(/^\/+/, '')
  if (normalized.startsWith('images/')) return `/${normalized}`
  return `/images/${normalized}`
})

const productAttributes = computed(() => {
  if (!product.value) return []
  
  const type = productTypes.value.find(t => t.id === product.value?.productTypeId)
  if (!type) return []
  
  return type.attributes.map(attrDef => {
    const attrValue = product.value?.attributes.find(
      a => a.productAttributeId === attrDef.id
    )
    return {
      ...attrDef,
      value: attrValue?.value || null,
    }
  })
})

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

const getUnitTypeName = (unitType: string): string => {
  const types: Record<string, string> = {
    base: 'Базовая',
    package: 'Упаковка',
    portion: 'Порция',
  }
  return types[unitType] || unitType
}

const getBaseUnitLabel = (): string => {
  const unit = units.value.find(u => u.id === product.value?.baseUnitId)
  return unit ? `${unit.description} (${unit.code})` : `#${product.value?.baseUnitId}`
}

const formatAttributeValue = (attr: any): string => {
  if (attr.value === null || attr.value === undefined) return '—'
  
  switch (attr.dataType) {
    case 'boolean':
      return attr.value === 'true' ? '✅ Да' : '❌ Нет'
    case 'number':
      const numValue = parseFloat(String(attr.value))
      return isNaN(numValue) ? '—' : formatNumber(numValue)
    default:
      return String(attr.value)
  }
}

const calculateUnitPrice = (ratioToBase: number): number => {
  if (!product.value) return 0
  return product.value.baseCost * ratioToBase
}

const calculateUnitsInBase = (ratioToBase: number): string => {
  if (ratioToBase <= 0) return '∞'
  const units = 1 / ratioToBase
  return formatNumber(units)
}

const getExampleIcon = (type: string): string => {
  const icons: Record<string, string> = {
    base_unit_sale: '📏',
    fractional_unit_sale: '🔢',
    component_usage: '📦',
  }
  return icons[type] || '💡'
}

const loadProduct = async () => {
  try {
    loading.value = true
    error.value = null
    
    const [productData, typesData, unitsData] = await Promise.all([
      productApi2.getProductView(productId.value),
      productApi2.getProductTypes(),
      productApi2.getUnits(),
    ])
    
    product.value = productData
    productTypes.value = typesData
    units.value = unitsData
    
    // Load fractional units
    try {
      fractionalUnits.value = await productApi2.getFractionalUnits(productId.value)
    } catch (e) {
      console.warn('Failed to load fractional units:', e)
    }
    
    // Load component tree for composite products
    if (productData.isComposite) {
      try {
        componentTree.value = await productApi2.getComponentTree(productId.value)
      } catch (e) {
        console.warn('Failed to load component tree:', e)
      }
    }
    
    // Load usage examples
    try {
      usageExamples.value = await productApi2.getUsageExamples(productId.value)
    } catch (e) {
      console.warn('Failed to load usage examples:', e)
    }
  } catch (err: any) {
    console.error('Error loading product:', err)
    error.value = err.response?.data?.detail || 'Не удалось загрузить информацию о продукте'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/products2')
}

const editProduct = () => {
  router.push(`/products2/${productId.value}/edit`)
}

// Lifecycle
onMounted(() => {
  loadProduct()
})
</script>

<style scoped>
.product-view-2-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background: #f8fafc;
  min-height: 100vh;
}

/* Header */
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.breadcrumb-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}

.breadcrumb-separator {
  color: #cbd5e1;
}

.breadcrumb-current {
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Loading & Error States */
.loading-state,
.error-state {
  padding: 60px 20px;
  text-align: center;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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

.error-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.error-state h3 {
  margin: 0 0 8px 0;
  color: #1e293b;
}

.error-state p {
  margin: 0 0 16px 0;
  color: #64748b;
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

/* Cards */
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.card-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.card-subtitle {
  margin: -12px 0 16px 0;
  font-size: 14px;
  color: #64748b;
}

.card-header-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* Product Main Card */
.product-main-card {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 24px;
}

.product-image-section {
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-container {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  width: 100%;
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border: 2px dashed #e2e8f0;
  border-radius: 8px;
  color: #94a3b8;
}

.no-image-icon {
  font-size: 64px;
  margin-bottom: 8px;
}

.product-basic-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.product-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.sku-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #f1f5f9;
  border-radius: 6px;
  font-family: monospace;
  font-size: 13px;
  color: #475569;
  flex-shrink: 0;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: #64748b;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.price-value {
  color: #10b981;
}

.stock-value {
  color: #10b981;
}

.stock-value.low-stock {
  color: #f59e0b;
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

/* Attributes */
.attributes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.attribute-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.attribute-name {
  font-weight: 600;
  color: #475569;
}

.attribute-value {
  color: #1e293b;
}

/* Fractional Units */
.units-table-wrapper {
  overflow-x: auto;
}

.units-table {
  width: 100%;
  border-collapse: collapse;
}

.units-table th {
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

.units-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.unit-row:hover {
  background: #f8fafc;
}

.unit-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.base-unit-indicator {
  font-size: 16px;
}

.unit-code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #475569;
}

.unit-type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.unit-type-badge.type-base {
  background: #dbeafe;
  color: #1d4ed8;
}

.unit-type-badge.type-package {
  background: #fef3c7;
  color: #92400e;
}

.unit-type-badge.type-portion {
  background: #dcfce7;
  color: #166534;
}

.ratio-value {
  font-family: monospace;
  color: #475569;
}

.sales-count {
  font-weight: 600;
  color: #64748b;
}

/* Component Tree */
.component-tree {
  margin-top: 16px;
}

/* Components List */
.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.component-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.component-card-header {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.component-name {
  font-weight: 600;
  color: #1e293b;
  display: block;
  margin-bottom: 4px;
}

.component-sku {
  font-size: 12px;
  color: #94a3b8;
  font-family: monospace;
}

.component-card-body {
  padding: 12px 16px;
}

.component-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
}

.stat-value {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.stat-value.allowed {
  color: #16a34a;
}

.stat-value.not-allowed {
  color: #dc2626;
}

.component-card-footer {
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
}

/* Usage Examples */
.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.example-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.example-card-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.example-card-content {
  flex: 1;
}

.example-card-title {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.example-card-description {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #64748b;
}

.example-card-ratio {
  font-size: 12px;
  color: #94a3b8;
}

.example-card-ratio code {
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

/* Stock Table */
.stock-table-wrapper {
  overflow-x: auto;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
}

.stock-table th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.stock-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.stock-units {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.stock-unit-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 12px;
  color: #475569;
}

/* Empty State */
.empty-state-small {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
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
  text-decoration: none;
  display: inline-block;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

/* Responsive */
@media (max-width: 1024px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .product-main-card {
    grid-template-columns: 1fr;
  }
}
</style>
