<template>
  <div class="product-form-2-container">
    <!-- Form Header with Preview -->
    <div class="form-header-section">
      <div class="header-info">
        <h3>{{ isEditing ? '✏️ Редактирование' : '➕ Создание' }}</h3>
        <p class="header-subtitle">
          {{ isEditing ? `Продукт #${productIdValue}` : 'Заполните форму для создания нового продукта' }}
        </p>
      </div>
      <div class="header-actions">
        <button type="button" @click="cancel" class="btn btn-outline">
          ← Назад
        </button>
        <button 
          v-if="isEditing && productIdValue" 
          type="button" 
          @click="goToProductView" 
          class="btn btn-info"
        >
          👁️ Просмотр
        </button>
      </div>
    </div>

    <form @submit.prevent="handleSubmit" class="product-form">
      <!-- Main Properties Card -->
      <div class="form-card">
        <h4 class="card-title">📋 Основная информация</h4>
        
        <div class="form-grid">
          <!-- Product Type -->
          <div class="form-group full-width">
            <label class="form-label">
              Тип продукта <span class="required">*</span>
            </label>
            <select
              v-model.number="form.productTypeId"
              required
              @change="onTypeChange"
              :disabled="isEditing"
              class="form-control"
              :class="{ 'has-error': errors.productTypeId }"
            >
              <option :value="null">Выберите тип продукта...</option>
              <option v-for="type in productTypes" :key="type.id" :value="type.id">
                {{ type.name }} {{ type.isComposite ? '(Составной)' : '' }}
              </option>
            </select>
            <span v-if="errors.productTypeId" class="error-message">{{ errors.productTypeId }}</span>
            <div v-if="currentType" class="type-info">
              <span class="type-badge" :class="currentType.isComposite ? 'composite' : 'simple'">
                {{ currentType.isComposite ? '📦 Составной тип' : '🔹 Простой тип' }}
              </span>
              <span v-if="currentType.strictUnitsByType" class="strict-badge">
                🔒 Строгий режим единиц
              </span>
            </div>
          </div>

          <!-- Name -->
          <div class="form-group full-width">
            <label class="form-label">
              Название <span class="required">*</span>
            </label>
            <input
              v-model="form.name"
              type="text"
              placeholder="Введите название продукта"
              required
              class="form-control"
              :class="{ 'has-error': errors.name }"
            />
            <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
          </div>

          <!-- SKU -->
          <div class="form-group">
            <label class="form-label">SKU (артикул)</label>
            <input
              v-model="form.sku"
              type="text"
              placeholder="WINE-001"
              class="form-control"
            />
          </div>

          <!-- Base Cost -->
          <div class="form-group">
            <label class="form-label">
              Базовая стоимость <span class="required">*</span>
            </label>
            <div class="input-with-prefix">
              <span class="prefix">€</span>
              <input
                v-model.number="form.baseCost"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                required
                class="form-control"
                :class="{ 'has-error': errors.baseCost }"
              />
            </div>
            <span v-if="errors.baseCost" class="error-message">{{ errors.baseCost }}</span>
          </div>

          <!-- Base Unit -->
          <div class="form-group full-width">
            <label class="form-label">
              Базовая единица измерения <span class="required">*</span>
            </label>
            <select
              v-model.number="form.baseUnitId"
              required
              class="form-control"
              :class="{ 'has-error': errors.baseUnitId }"
            >
              <option :value="null">Выберите базовую единицу...</option>
              <option v-for="unit in units" :key="unit.id" :value="unit.id">
                {{ unit.description }} ({{ unit.code }}) — {{ getUnitTypeName(unit.unitType) }}
              </option>
            </select>
            <span v-if="errors.baseUnitId" class="error-message">{{ errors.baseUnitId }}</span>
          </div>
        </div>
      </div>

      <!-- Attributes Card -->
      <div v-if="currentTypeAttributes.length > 0" class="form-card">
        <h4 class="card-title">🏷️ Атрибуты</h4>
        <div class="attributes-grid">
          <div 
            v-for="attr in currentTypeAttributes" 
            :key="attr.id" 
            class="attribute-item"
            :class="{ 'required-field': attr.isRequired }"
          >
            <label class="attribute-label">
              {{ attr.name }}
              <span v-if="attr.isRequired" class="required">*</span>
              <span v-if="attr.unitId" class="unit-hint">
                ({{ getUnitLabel(attr.unitId) }})
              </span>
            </label>

            <!-- Number Input -->
            <input
              v-if="attr.dataType === 'number'"
              v-model.number="form.attributes[attr.code]"
              type="number"
              step="0.01"
              :placeholder="`Введите ${attr.name.toLowerCase()}`"
              :required="attr.isRequired"
              class="form-control"
            />

            <!-- String Input -->
            <input
              v-else-if="attr.dataType === 'string'"
              v-model="form.attributes[attr.code]"
              type="text"
              :placeholder="`Введите ${attr.name.toLowerCase()}`"
              :required="attr.isRequired"
              class="form-control"
            />

            <!-- Boolean Checkbox -->
            <div v-else-if="attr.dataType === 'boolean'" class="checkbox-wrapper">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="form.attributes[attr.code]"
                  class="checkbox-input"
                />
                <span class="checkbox-text">
                  {{ form.attributes[attr.code] ? 'Да' : 'Нет' }}
                </span>
              </label>
            </div>

            <span v-if="errors.attributes && (errors.attributes as any)[attr.code]" class="error-message">
              {{ (errors.attributes as any)[attr.code] }}
            </span>
          </div>
        </div>
      </div>

      <!-- Fractional Units Card -->
      <div class="form-card">
        <div class="card-header-with-action">
          <h4 class="card-title">📏 Дробные единицы измерения</h4>
          <div class="card-actions">
            <button 
              type="button" 
              @click="applyTypeUnits" 
              class="btn btn-sm btn-outline"
              :disabled="!currentType || !currentType.productTypeUnits?.length"
            >
              📋 Из типа продукта
            </button>
          </div>
        </div>

        <div v-if="currentType?.strictUnitsByType" class="strict-mode-notice">
          🔒 <strong>Строгий режим:</strong> Разрешены только единицы из типа продукта
        </div>

        <div class="units-list">
          <!-- Base Unit (always first, read-only) -->
          <div v-if="form.baseUnitId" class="unit-item base-unit">
            <div class="unit-header">
              <span class="unit-badge">📏 Базовая</span>
              <span class="unit-name">{{ getUnitLabel(form.baseUnitId) }}</span>
            </div>
            <div class="unit-values">
              <div class="unit-value">
                <span class="value-label">Ratio:</span>
                <span class="value">1.000000</span>
              </div>
            </div>
            <span class="unit-note">Неизменяемая базовая единица</span>
          </div>

          <!-- Additional Units -->
          <div 
            v-for="(pu, index) in additionalUnits" 
            :key="index" 
            class="unit-item"
          >
            <div class="unit-header">
              <select
                v-model.number="pu.unitId"
                class="form-control unit-select"
                :disabled="currentType?.strictUnitsByType && !isUnitAllowed(pu.unitId)"
              >
                <option :value="null">Выберите единицу...</option>
                <option 
                  v-for="unit in getAvailableUnits(pu.unitId)" 
                  :key="unit.id" 
                  :value="unit.id"
                >
                  {{ unit.description }} ({{ unit.code }})
                </option>
              </select>
              <button 
                type="button" 
                @click="removeUnit(index)" 
                class="btn btn-sm btn-danger"
                title="Удалить единицу"
              >
                🗑️
              </button>
            </div>
            <div class="unit-values">
              <div class="unit-value-group">
                <label class="value-label">Ratio к базовой:</label>
                <input
                  v-model.number="pu.ratioToBase"
                  type="number"
                  step="0.000001"
                  min="0.000001"
                  class="form-control value-input"
                  placeholder="0.000000"
                />
              </div>
              <div class="unit-value-group">
                <label class="value-label">Дискретный шаг:</label>
                <input
                  v-model.number="pu.discreteStep"
                  type="number"
                  step="0.000001"
                  min="0"
                  class="form-control value-input"
                  placeholder="Необязательно"
                />
              </div>
            </div>
            <div v-if="pu.ratioToBase" class="unit-calculation">
              1 {{ getUnitName(pu.unitId) }} = {{ pu.ratioToBase }} базовой ×
              <span v-if="form.baseCost">€{{ (Number(form.baseCost) * pu.ratioToBase).toFixed(2) }}</span>
            </div>
          </div>

          <!-- Add Unit Button -->
          <button type="button" @click="addUnit" class="btn btn-outline btn-dashed">
            ➕ Добавить единицу измерения
          </button>
        </div>
      </div>

      <!-- Components Card (for composite products) -->
      <div v-if="currentType?.isComposite" class="form-card composite-card">
        <div class="card-header-with-action">
          <h4 class="card-title">📦 Компоненты составного продукта</h4>
        </div>

        <div v-if="form.components.length === 0" class="empty-components">
          <p>У этого продукта ещё нет компонентов</p>
          <button type="button" @click="addComponent" class="btn btn-primary">
            ➕ Добавить первый компонент
          </button>
        </div>

        <div v-else class="components-list">
          <div 
            v-for="(comp, index) in form.components" 
            :key="index" 
            class="component-item"
          >
            <div class="component-number">{{ index + 1 }}</div>
            <div class="component-fields">
              <div class="component-row">
                <div class="component-field">
                  <label class="component-label">Ингредиент</label>
                  <select
                    v-model.number="comp.ingredientId"
                    class="form-control"
                  >
                    <option :value="null">Выберите ингредиент...</option>
                    <option
                      v-for="ingredient in getComponentCandidates()"
                      :key="ingredient.id"
                      :value="ingredient.id"
                    >
                      {{ ingredient.name }} ({{ ingredient.code }})
                    </option>
                  </select>
                </div>
                <div class="component-field">
                  <label class="component-label">Количество</label>
                  <input
                    v-model.number="comp.quantity"
                    type="number"
                    step="0.001"
                    min="0.001"
                    class="form-control"
                    placeholder="0.000"
                  />
                </div>
                <div class="component-field">
                  <label class="component-label">Единица измерения</label>
                  <select
                    v-model.number="comp.unitId"
                    class="form-control"
                  >
                    <option :value="null">Авто (базовая компонента)</option>
                    <option v-for="unit in units" :key="unit.id" :value="unit.id">
                      {{ unit.description }} ({{ unit.code }})
                    </option>
                  </select>
                </div>
              </div>
              <div class="component-row">
                <div class="component-field checkbox-field">
                  <label class="checkbox-label-small">
                    <input
                      type="checkbox"
                      v-model="comp.substitutionAllowed"
                    />
                    Разрешены замены
                  </label>
                </div>
                <div class="component-field">
                  <label class="component-label">Округление</label>
                  <input
                    v-model="comp.rounding"
                    type="text"
                    placeholder="Например: 0.01"
                    class="form-control"
                  />
                </div>
                <div class="component-actions">
                  <button 
                    type="button" 
                    @click="removeComponent(index)" 
                    class="btn btn-sm btn-danger"
                  >
                    🗑️ Удалить
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="currentType?.isComposite" class="add-component-section">
          <button type="button" @click="addComponent" class="btn btn-outline btn-dashed">
            ➕ Добавить компонент
          </button>
        </div>
      </div>

      <!-- Usage Examples (for existing products) -->
      <div v-if="isEditing && usageExamples.length > 0" class="form-card">
        <h4 class="card-title">💡 Примеры использования</h4>
        <div class="examples-list">
          <div v-for="(example, index) in usageExamples" :key="index" class="example-item">
            <div class="example-icon">
              {{ getExampleIcon(example.type) }}
            </div>
            <div class="example-content">
              <div class="example-title">{{ example.title }}</div>
              <div class="example-description">{{ example.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Form Actions -->
      <div class="form-actions">
        <button type="submit" class="btn btn-primary btn-lg" :disabled="saving">
          {{ saving ? '⏳ Сохранение...' : (isEditing ? '💾 Обновить' : '✨ Создать') }}
        </button>
        <button type="button" @click="cancel" class="btn btn-outline">
          Отмена
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import type {
  ProductView,
  ProductType,
  Unit,
  Ingredient,
  ProductAttributeDefinition,
  ProductUsageExample,
  ProductForm as ProductFormType,
} from '@/api/productApi2'
import { productApi2 } from '@/api/productApi2'

// Props and emits
const props = defineProps<{
  productId?: number | null
}>()

const emit = defineEmits(['close', 'saved'])

const router = useRouter()

// State
const productTypes = ref<ProductType[]>([])
const units = ref<Unit[]>([])
const ingredients = ref<Ingredient[]>([])
const productView = ref<ProductView | null>(null)
const usageExamples = ref<ProductUsageExample[]>([])
const saving = ref(false)
const errors = ref<Record<string, string>>({})

const form = ref<ProductFormType>({
  productTypeId: 0,
  name: '',
  sku: '',
  baseCost: '0',
  stock: '0',
  baseUnitId: 0,
  isComposite: false,
  attributes: {},
  components: [],
  productUnits: [],
})

// Computed
const isEditing = computed(() => !!props.productId)
const productIdValue = computed(() => (props.productId ? Number(props.productId) : null))

const currentType = computed(() =>
  productTypes.value.find(t => t.id === form.value.productTypeId)
)

const currentTypeAttributes = computed(() => {
  const attrs = currentType.value?.attributes || []
  return [...attrs].sort((a, b) => a.sortOrder - b.sortOrder)
})

const additionalUnits = computed({
  get: () => {
    return form.value.productUnits.filter(pu => pu.unitId !== form.value.baseUnitId)
  },
  set: (value) => {
    const baseUnit = form.value.productUnits.find(pu => pu.unitId === form.value.baseUnitId)
    form.value.productUnits = baseUnit ? [baseUnit, ...value] : value
  },
})

// Methods
const getUnitTypeName = (unitType: string): string => {
  const types: Record<string, string> = {
    base: 'Базовая',
    package: 'Упаковка',
    portion: 'Порция',
  }
  return types[unitType] || unitType
}

const getUnitLabel = (unitId: number): string => {
  const unit = units.value.find(u => u.id === unitId)
  return unit ? `${unit.description} (${unit.code})` : `#${unitId}`
}

const getUnitName = (unitId: number): string => {
  const unit = units.value.find(u => u.id === unitId)
  return unit?.code || ''
}

const isUnitAllowed = (unitId: number): boolean => {
  if (!currentType.value?.strictUnitsByType) return true
  const allowedUnitIds = new Set(
    (currentType.value.productTypeUnits || []).map(u => u.unitId)
  )
  allowedUnitIds.add(form.value.baseUnitId)
  return allowedUnitIds.has(unitId)
}

const getAvailableUnits = (currentUnitId: number): Unit[] => {
  if (!currentType.value?.strictUnitsByType) return units.value
  
  const allowedUnitIds = new Set(
    (currentType.value.productTypeUnits || []).map(u => u.unitId)
  )
  allowedUnitIds.add(form.value.baseUnitId)
  
  return units.value.filter(u => allowedUnitIds.has(u.id) || u.id === currentUnitId)
}

const getComponentCandidates = (): Ingredient[] => {
  return ingredients.value
}

const getExampleIcon = (type: string): string => {
  const icons: Record<string, string> = {
    base_unit_sale: '📏',
    fractional_unit_sale: '🔢',
    component_usage: '📦',
  }
  return icons[type] || '💡'
}

const onTypeChange = () => {
  form.value.attributes = {}
  form.value.isComposite = currentType.value?.isComposite || false
  
  if (!currentType.value?.isComposite) {
    form.value.components = []
  }
  
  if (!isEditing.value || !form.value.productUnits.length) {
    applyTypeUnits()
  }
}

const applyTypeUnits = () => {
  const typeUnits = currentType.value?.productTypeUnits || []
  const normalized = typeUnits
    .map(row => ({
      unitId: Number(row.unitId ?? 0),
      ratioToBase: Number(row.ratioToBase ?? 1),
      discreteStep: row.discreteStep ?? null,
    }))
    .filter(row => row.unitId > 0)
  
  form.value.productUnits = normalized
  ensureBaseUnitBinding()
}

const ensureBaseUnitBinding = () => {
  const baseUnitId = Number(form.value.baseUnitId || 0)
  if (!baseUnitId) return

  const existingIndex = form.value.productUnits.findIndex(row => row.unitId === baseUnitId)

  if (existingIndex >= 0) {
    const existingUnit = form.value.productUnits[existingIndex]
    if (existingUnit) {
      existingUnit.ratioToBase = 1
      existingUnit.discreteStep = null
    }
  } else {
    form.value.productUnits.unshift({
      unitId: baseUnitId,
      ratioToBase: 1,
      discreteStep: null,
    })
  }
}

const addUnit = () => {
  additionalUnits.value.push({
    unitId: 0,
    ratioToBase: 1,
    discreteStep: null,
  })
}

const removeUnit = (index: number) => {
  const row = additionalUnits.value[index]
  if (row && row.unitId === form.value.baseUnitId) {
    alert('Базовую единицу нельзя удалить')
    return
  }
  additionalUnits.value.splice(index, 1)
}

const addComponent = () => {
  form.value.components.push({
    ingredientId: 0,
    quantity: 1,
    unitId: undefined,
    substitutionAllowed: false,
    rounding: undefined,
  })
}

const removeComponent = (index: number) => {
  form.value.components.splice(index, 1)
}

const toInitialAttributes = (product: ProductView, type: ProductType): Record<string, any> => {
  const initialAttributes: Record<string, any> = {}
  
  for (const def of type.attributes || []) {
    const apiAttr = (product.attributes || []).find(
      a => a.productAttributeId === def.id
    )
    
    let value: any = null
    if (apiAttr) {
      switch (def.dataType) {
        case 'number':
          value = parseFloat(apiAttr.value) || 0
          break
        case 'boolean':
          value = apiAttr.value === 'true'
          break
        case 'string':
          value = apiAttr.value
          break
        default:
          value = apiAttr.value
      }
    } else {
      value = def.dataType === 'number' ? 0 : def.dataType === 'boolean' ? false : ''
    }
    
    initialAttributes[def.code] = value
  }
  
  return initialAttributes
}

const loadProductForEdit = async (productId: number) => {
  try {
    const product = await productApi2.getProductView(productId)
    productView.value = product
    
    const type = productTypes.value.find(t => t.id === product.productTypeId)
    if (!type) {
      throw new Error('Тип продукта не найден')
    }
    
    const initialComponents = (product.components || []).map(comp => ({
      ingredientId: comp.ingredientId,
      quantity: Number(comp.quantity),
      unitId: comp.unitId,
      substitutionAllowed: comp.substitutionAllowed,
      rounding: comp.rounding,
    }))
    
    const productUnits = (product.productUnits || []).map(pu => ({
      unitId: pu.unitId ?? 0,
      ratioToBase: Number(pu.ratioToBase ?? 1),
      discreteStep: pu.discreteStep ?? null,
    }))
    
    form.value = {
      productTypeId: Number(product.productTypeId),
      name: product.name,
      sku: product.sku || '',
      baseCost: String(product.baseCost),
      stock: String(product.stock),
      baseUnitId: product.baseUnitId || 0,
      isComposite: type.isComposite,
      attributes: toInitialAttributes(product, type),
      components: type.isComposite ? initialComponents : [],
      productUnits: productUnits,
    }
    
    ensureBaseUnitBinding()
    
    // Load usage examples
    try {
      usageExamples.value = await productApi2.getUsageExamples(productId)
    } catch (e) {
      console.warn('Failed to load usage examples:', e)
    }
  } catch (error) {
    console.error('Error loading product:', error)
    alert('Ошибка при загрузке продукта')
    emit('close')
  }
}

const validateForm = (): boolean => {
  errors.value = {}
  
  if (!form.value.productTypeId || form.value.productTypeId <= 0) {
    errors.value.productTypeId = 'Выберите тип продукта'
    return false
  }
  
  if (!form.value.name || !form.value.name.trim()) {
    errors.value.name = 'Введите название продукта'
    return false
  }
  
  const baseCostNum = Number(form.value.baseCost)
  if (!form.value.baseCost || baseCostNum < 0) {
    errors.value.baseCost = 'Введите корректную стоимость'
    return false
  }
  
  if (!form.value.baseUnitId || form.value.baseUnitId <= 0) {
    errors.value.baseUnitId = 'Выберите базовую единицу'
    return false
  }
  
  for (const attr of currentTypeAttributes.value) {
    const attrValue = form.value.attributes[attr.code]
    if (attr.isRequired && (attrValue === '' || attrValue == null)) {
      errors.value[`attributes.${attr.code}`] = `Обязательное поле: ${attr.name}`
      return false
    }
  }
  
  return true
}

const handleSubmit = async () => {
  if (!validateForm()) {
    alert('Пожалуйста, исправьте ошибки в форме')
    return
  }
  
  try {
    saving.value = true
    
    if (isEditing.value && props.productId) {
      await productApi2.updateProduct(props.productId, form.value)
      alert('Продукт обновлён! ✨')
    } else {
      await productApi2.createProduct(form.value)
      alert('Продукт создан! 🎉')
    }
    
    emit('saved')
  } catch (error: any) {
    console.error('Error saving product:', error)
    alert(error.response?.data?.detail || 'Ошибка при сохранении продукта')
  } finally {
    saving.value = false
  }
}

const cancel = () => {
  emit('close')
}

const goToProductView = () => {
  if (productIdValue.value) {
    router.push(`/products2/${productIdValue.value}`)
  }
}

// Lifecycle
onMounted(async () => {
  try {
    const [types, unitsData, ingredientsData] = await Promise.all([
      productApi2.getProductTypes(),
      productApi2.getUnits(),
      productApi2.getIngredients(),
    ])
    
    productTypes.value = types
    units.value = unitsData
    ingredients.value = ingredientsData
    
    if (isEditing.value && props.productId) {
      await loadProductForEdit(Number(props.productId))
    } else {
      form.value = {
        productTypeId: 0,
        name: '',
        sku: '',
        baseCost: '0',
        stock: '0',
        baseUnitId: 0,
        isComposite: false,
        attributes: {},
        components: [],
        productUnits: [],
      }
    }
  } catch (error) {
    console.error('Error loading reference data:', error)
    alert('Ошибка при загрузке данных')
    emit('close')
  }
})

watch(
  () => form.value.baseUnitId,
  () => {
    ensureBaseUnitBinding()
  }
)
</script>

<style scoped>
.product-form-2-container {
  max-width: 1000px;
  margin: 0 auto;
}

/* Form Header */
.form-header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.header-info h3 {
  margin: 0 0 4px 0;
  font-size: 20px;
  color: #1e293b;
}

.header-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Form Cards */
.form-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.card-title {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.card-header-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

/* Form Grid */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-label {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}

.required {
  color: #ef4444;
}

.form-control {
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
  background: white;
}

.form-control:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-control.has-error {
  border-color: #ef4444;
}

.error-message {
  font-size: 12px;
  color: #ef4444;
  margin-top: 4px;
}

/* Type Info */
.type-info {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.type-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.type-badge.composite {
  background: #fef3c7;
  color: #92400e;
}

.type-badge.simple {
  background: #dbeafe;
  color: #1d4ed8;
}

.strict-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

/* Input with Prefix */
.input-with-prefix {
  display: flex;
  align-items: center;
}

.prefix {
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-right: none;
  border-radius: 8px 0 0 8px;
  font-weight: 600;
  color: #475569;
}

.input-with-prefix .form-control {
  border-radius: 0 8px 8px 0;
}

/* Attributes */
.attributes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.attribute-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.attribute-item.required-field {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.attribute-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}

.unit-hint {
  font-weight: 400;
  color: #94a3b8;
  font-size: 12px;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-text {
  font-size: 14px;
  color: #475569;
}

/* Units List */
.units-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.unit-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.unit-item.base-unit {
  background: #eff6ff;
  border-color: #3b82f6;
}

.unit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.unit-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #3b82f6;
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.unit-name {
  font-weight: 600;
  color: #1e293b;
}

.unit-select {
  flex: 1;
  margin-right: 12px;
}

.unit-values {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.unit-value-group {
  flex: 1;
}

.value-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.value-input {
  width: 100%;
}

.unit-calculation {
  font-size: 13px;
  color: #64748b;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.unit-note {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}

.strict-mode-notice {
  padding: 12px 16px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #92400e;
}

.btn-dashed {
  width: 100%;
  border-style: dashed;
}

/* Components */
.composite-card {
  border: 2px solid #dbeafe;
}

.empty-components {
  text-align: center;
  padding: 40px 20px;
  color: #64748b;
}

.components-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.component-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.component-number {
  width: 32px;
  height: 32px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.component-fields {
  flex: 1;
}

.component-row {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.component-row:last-child {
  margin-bottom: 0;
}

.component-field {
  flex: 1;
}

.component-field.checkbox-field {
  flex: none;
  display: flex;
  align-items: center;
}

.component-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.checkbox-label-small {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
}

.component-actions {
  display: flex;
  align-items: flex-end;
}

.add-component-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

/* Usage Examples */
.examples-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.example-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.example-icon {
  font-size: 24px;
}

.example-content {
  flex: 1;
}

.example-title {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.example-description {
  font-size: 13px;
  color: #64748b;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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
  padding: 12px 24px;
  font-size: 15px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}
</style>
