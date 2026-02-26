<template>
  <div class="product-type-management">
    <h2>Управление типами товаров</h2>

    <div class="search-card">
      <button v-if="hasPermission('product_type.write')" @click="showCreateDialog" class="btn btn-primary">Создать тип товара</button>
    </div>

    <div v-if="loading">Загрузка...</div>
    <table v-else class="product-type-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Название</th>
          <th>Описание</th>
          <th>Составной</th>
          <th>Атрибуты</th>
          <th>Юниты типа</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="productType in productTypes" :key="productType.id">
          <td>{{ productType.id }}</td>
          <td>{{ productType.name }}</td>
          <td>{{ productType.description }}</td>
          <td>
            <span :class="{'tag-success': productType.isComposite, 'tag-info': !productType.isComposite}">
              {{ productType.isComposite ? 'Да' : 'Нет' }}
            </span>
          </td>
          <td>
            <span v-for="attr in productType.attributes" :key="attr.id" class="tag">
              {{ attr.name }}
            </span>
          </td>
          <td>
            <span v-for="unit in productType.productTypeUnits || []" :key="`ptu-${productType.id}-${unit.unitId}`" class="tag">
              {{ unitDisplay(unit.unitId) }} × {{ unit.ratioToBase }}
            </span>
            <span v-if="!(productType.productTypeUnits || []).length" class="tag tag-muted">—</span>
          </td>
          <td>
            <button v-if="hasPermission('product_type.write')" @click="editProductType(productType)" class="btn btn-sm">Редактировать</button>
            <button v-if="hasPermission('product_type.delete')" @click="deleteProductType(productType.id)" class="btn btn-sm btn-danger">Удалить</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Modal for creating/editing product type -->
    <div v-if="dialogVisible" class="modal-overlay" @click="closeDialog">
      <div class="modal-content" @click.stop>
        <h3>{{ editingProductType ? 'Редактировать тип товара' : 'Создать тип товара' }}</h3>

        <form @submit.prevent="saveProductType">
          <div class="form-group">
            <label>Название:</label>
            <input v-model="form.name" placeholder="Введите название типа товара" required />
          </div>

          <div class="form-group">
            <label>Описание:</label>
            <textarea v-model="form.description" placeholder="Введите описание"></textarea>
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="form.isComposite" />
              Составной тип
            </label>
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="form.strictUnitsByType" />
              Строгие юниты по типу (товару разрешены только юниты типа)
            </label>
          </div>

          <h4>Атрибуты</h4>
          <button type="button" @click="addAttribute" class="btn btn-secondary">Добавить атрибут</button>

          <div v-for="(attr, index) in form.attributes" :key="index" class="attribute-card">
            <div class="card-header">
              <span>Атрибут {{ index + 1 }}</span>
              <button
                type="button"
                @click="removeAttribute(index)"
                :disabled="form.attributes.length <= 1"
                class="btn btn-sm btn-danger"
              >
                Удалить
              </button>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Название:</label>
                <input v-model="attr.name" placeholder="Название атрибута" required />
              </div>

              <div class="form-group">
                <label>Код:</label>
                <input v-model="attr.code" placeholder="Код атрибута" required />
              </div>

              <div class="form-group">
                <label>Тип данных:</label>
                <select v-model="attr.dataType" required>
                  <option value="number">Число</option>
                  <option value="string">Строка</option>
                  <option value="boolean">Логический</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Единица измерения:</label>
                <select v-model="attr.unitId">
                  <option value="">Не выбрана</option>
                  <option
                    v-for="unit in units"
                    :key="unit.id"
                    :value="unit.id"
                  >
                    {{ unitDisplay(unit.id) }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>
                  <input type="checkbox" v-model="attr.isRequired" />
                  Обязательный
                </label>
              </div>

              <div class="form-group">
                <label>Порядок:</label>
                <input
                  type="number"
                  v-model.number="attr.sortOrder"
                  placeholder="Порядок отображения"
                  min="1"
                />
              </div>
            </div>
          </div>

          <h4>Юниты типа</h4>
          <button type="button" @click="addTypeUnit" class="btn btn-secondary">Добавить юнит типа</button>
          <div v-for="(unitRow, index) in form.productTypeUnits" :key="`type-unit-${index}`" class="attribute-card">
            <div class="card-header">
              <span>Юнит {{ index + 1 }}</span>
              <button
                type="button"
                @click="removeTypeUnit(index)"
                class="btn btn-sm btn-danger"
              >
                Удалить
              </button>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Единица</label>
                <select v-model.number="unitRow.unitId" required>
                  <option :value="0">Выберите единицу</option>
                  <option v-for="unit in units" :key="unit.id" :value="unit.id">
                    {{ unitDisplay(unit.id) }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Коэффициент к базе</label>
                <input v-model.number="unitRow.ratioToBase" type="number" min="0.000001" step="0.000001" required />
              </div>
              <div class="form-group">
                <label>Дискретный шаг</label>
                <input v-model.number="unitRow.discreteStep" type="number" min="0" step="0.000001" />
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeDialog" class="btn">Отмена</button>
            <button type="submit" class="btn btn-primary">Сохранить</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { ProductType, AttributeDefinition, Unit } from '@/api/productApi'
import { productApi } from '@/api/productApi'

// Auth store
const authStore = useAuthStore();

// Check permission function
const hasPermission = (permission: string): boolean => {
  return authStore.hasPermission(permission);
};

// State
const productTypes = ref<ProductType[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingProductType = ref<ProductType | null>(null)

type EditableAttribute = Omit<AttributeDefinition, 'id' | 'unitId'> & {
  id?: number
  unitId: number | null
}

type ProductTypeFormState = {
  id: number
  name: string
  description: string
  isComposite: boolean
  strictUnitsByType: boolean
  attributes: EditableAttribute[]
  productTypeUnits: Array<{ unitId: number; ratioToBase: number; discreteStep: number | null }>
}

const createEmptyAttribute = (sortOrder: number): EditableAttribute => ({
  name: '',
  code: '',
  dataType: 'string',
  unitId: null,
  isRequired: false,
  sortOrder,
})

// Form
const form = ref<ProductTypeFormState>({
  id: 0,
  name: '',
  description: '',
  isComposite: false,
  strictUnitsByType: false,
  attributes: [createEmptyAttribute(1)],
  productTypeUnits: [] as Array<{ unitId: number; ratioToBase: number; discreteStep: number | null }>
})

// Units (will be loaded from API)
const units = ref<Unit[]>([])

// Methods
const loadProductTypes = async () => {
  try {
    loading.value = true
    productTypes.value = await productApi.getProductTypes()
  } catch (error) {
    console.error('Error loading product types:', error)
  } finally {
    loading.value = false
  }
}

const loadUnits = async () => {
  units.value = await productApi.getUnits()
}

const unitDisplay = (unitId: number) => {
  const unit = units.value.find((row: any) => row.id === unitId)
  if (!unit) return `#${unitId}`
  return unit.description ? `${unit.description} (${unit.code})` : unit.code
}

const showCreateDialog = () => {
  resetForm()
  editingProductType.value = null
  dialogVisible.value = true
}

const editProductType = (productType: ProductType) => {
  editingProductType.value = productType
  form.value.id = productType.id
  form.value.name = productType.name
  form.value.description = productType.description || ''
  form.value.isComposite = productType.isComposite
  form.value.strictUnitsByType = !!productType.strictUnitsByType

  // Initialize attributes
  form.value.attributes = productType.attributes && productType.attributes.length > 0
    ? [...productType.attributes.map((attr) => ({
        ...attr,
        unitId: attr.unitId ?? null,
        sortOrder: attr.sortOrder || 1  // Ensure sortOrder is set
      }))]
    : []

  form.value.productTypeUnits = (productType.productTypeUnits || []).map((row: any) => ({
    unitId: Number(row.unitId ?? row.unit_id ?? 0),
    ratioToBase: Number(row.ratioToBase ?? row.ratio_to_base ?? 1),
    discreteStep: row.discreteStep ?? row.discrete_step ?? null,
  }))

  dialogVisible.value = true
}

const deleteProductType = async (id: number) => {
  if (confirm('Вы уверены, что хотите удалить этот тип товара?')) {
    try {
      await productApi.deleteProductType(id)
      await loadProductTypes()
    } catch (error) {
      console.error('Error deleting product type:', error)
      alert('Ошибка при удалении типа товара')
    }
  }
}

const addAttribute = () => {
  // Calculate the next sort order value
  const maxSortOrder = form.value.attributes.reduce((max, attr) => Math.max(max, attr.sortOrder || 0), 0)
  form.value.attributes.push(createEmptyAttribute(maxSortOrder + 1))
}

const removeAttribute = (index: number) => {
  // Используем Vue.set или прямое присваивание для обеспечения реактивности
  form.value.attributes.splice(index, 1)
  // Если массив стал пустым, добавим один пустой атрибут для удобства
  if (form.value.attributes.length === 0) {
    const maxSortOrder = form.value.attributes.reduce((max, attr) => Math.max(max, attr.sortOrder || 0), 0)
    form.value.attributes.push(createEmptyAttribute(maxSortOrder + 1))
  }
}

const resetForm = () => {
  form.value.id = 0
  form.value.name = ''
  form.value.description = ''
  form.value.isComposite = false
  form.value.strictUnitsByType = false
  form.value.attributes = []
  form.value.productTypeUnits = []
}

const addTypeUnit = () => {
  form.value.productTypeUnits.push({ unitId: 0, ratioToBase: 1, discreteStep: null })
}

const removeTypeUnit = (index: number) => {
  form.value.productTypeUnits.splice(index, 1)
}

const saveProductType = async () => {
  try {
    if (editingProductType.value) {
      // Update existing product type
      const payload = {
        name: form.value.name,
        description: form.value.description,
        is_composite: form.value.isComposite,
        strict_units_by_type: form.value.strictUnitsByType,
        attributes: form.value.attributes
          .filter(attr => attr.code.trim() !== '')  // Filter out attributes with empty codes
          .map(attr => ({
            product_type_id: form.value.id,
            name: attr.name,
            code: attr.code,
            data_type: attr.dataType,
            unit_id: attr.unitId || null,
            is_required: attr.isRequired,
            sort_order: attr.sortOrder || 1
          })),
        product_type_units: form.value.productTypeUnits
          .filter((row) => row.unitId > 0 && row.ratioToBase > 0)
          .map((row) => ({
            unit_id: row.unitId,
            ratio_to_base: row.ratioToBase,
            discrete_step: row.discreteStep ?? null,
          })),
      }

      // Use productApi for consistency
      await productApi.updateProductType(form.value.id, payload)
    } else {
      // Create new product type
      const payload = {
        name: form.value.name,
        description: form.value.description,
        is_composite: form.value.isComposite,
        strict_units_by_type: form.value.strictUnitsByType,
        attributes: form.value.attributes.map(attr => ({
          product_type_id: 0, // Will be set by backend
          name: attr.name,
          code: attr.code,
          data_type: attr.dataType,
          unit_id: attr.unitId || null,
          is_required: attr.isRequired,
          sort_order: attr.sortOrder || 1
        })),
        product_type_units: form.value.productTypeUnits
          .filter((row) => row.unitId > 0 && row.ratioToBase > 0)
          .map((row) => ({
            unit_id: row.unitId,
            ratio_to_base: row.ratioToBase,
            discrete_step: row.discreteStep ?? null,
          })),
      }

      // Use productApi for consistency
      await productApi.createProductType(payload)
    }

    closeDialog()
    await loadProductTypes()
    resetForm()
  } catch (error) {
    console.error('Error saving product type:', error)
    alert('Ошибка при сохранении типа товара')
  }
}

onMounted(async () => {
  await Promise.all([
    loadProductTypes(),
    loadUnits()
  ])
})

const closeDialog = () => {
  dialogVisible.value = false
}
</script>

<style scoped>
.product-type-management {
  padding: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.btn {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  background-color: #f5f5f5;
  margin-right: 5px;
  margin-bottom: 5px;
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

.product-type-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.product-type-table th,
.product-type-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.product-type-table th {
  background-color: #f2f2f2;
}

.tag {
  background-color: #e9ecef;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 4px;
}

.tag-muted {
  background-color: #f3f4f6;
  color: #6b7280;
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
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-row {
  display: flex;
  gap: 15px;
  margin-bottom: 10px;
}

.attribute-card {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 10px;
  background-color: #f9f9f9;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.modal-actions {
  margin-top: 20px;
  text-align: right;
}
</style>
