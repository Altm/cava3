<template>
  <div class="product-form-container">
    <div class="page-head">
      <h2>{{ isEditing ? 'Редактировать товар' : 'Создать товар' }}</h2>
      <div class="head-actions">
        <RouterLink class="btn btn-outline" to="/product-list">К списку</RouterLink>
        <RouterLink class="btn btn-outline" to="/product-units">Дробные части</RouterLink>
        <RouterLink
          v-if="isEditing && productIdValue"
          class="btn btn-secondary"
          :to="`/product-view/${productIdValue}`"
        >
          Просмотр
        </RouterLink>
        <RouterLink
          v-if="isEditing && productIdValue"
          class="btn btn-outline"
          :to="`/products/${productIdValue}/recipes/history`"
        >
          История рецептов
        </RouterLink>
      </div>
    </div>

    <div v-if="isEditing" class="preview-grid">
      <div class="card">
        <h3>Текущее состояние</h3>
        <div v-if="productView" class="meta">
          <div><b>ID:</b> {{ productView.id }}</div>
          <div><b>Название:</b> {{ productView.name }}</div>
          <div><b>Тип товара:</b> {{ currentType?.name ?? '-' }}</div>
          <div><b>Остаток:</b> {{ productView.stock }}</div>
          <div><b>Стоимость:</b> {{ productView.baseCost }}</div>
          <div><b>Составной:</b> {{ productView.isComposite ? 'Да' : 'Нет' }}</div>
          <div><b>Поставщик:</b> {{ productView.meta?.vendor ?? '-' }}</div>
          <div><b>Теги:</b> {{ productView.meta?.tags ?? '-' }}</div>
        </div>
        <div v-else class="muted">Загрузка данных...</div>
        <div v-if="isEditing && form.productUnits.length" class="units-summary">
          <div class="units-summary-head">
            <b>Привязанные юниты</b>
            <a class="anchor-link" href="#product-units">Редактировать ниже</a>
          </div>
          <div class="units-summary-list">
            <span
              v-for="pu in form.productUnits"
              :key="`${pu.unit_id}-${pu.ratio_to_base}`"
              class="unit-chip"
            >
              {{ unitOptionLabelById(pu.unit_id) }} × {{ pu.ratio_to_base }}
            </span>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Фото товара</h3>
        <div v-if="imageUrl" class="image-wrap">
          <img :src="imageUrl" :alt="form.name || 'Product image'" class="product-image" />
        </div>
        <div v-else class="muted">Фото не загружено</div>
        <div class="upload-controls">
          <input type="file" accept="image/*" @change="onImageSelected" class="form-control" />
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!selectedImageFile || imageUploading || !productIdValue"
            @click="uploadSelectedImage"
          >
            {{ imageUploading ? 'Загрузка...' : 'Загрузить фото' }}
          </button>
        </div>
      </div>
    </div>

    <form @submit.prevent="handleSubmit" class="product-form card">
      <!-- Тип товара -->
      <div class="form-group">
        <label>Тип товара *</label>
        <select
          v-model.number="form.productTypeId"
          required
          @change="onTypeChange"
          :disabled="isEditing"
          class="form-control"
        >
          <option :value="null">Выберите тип</option>
          <option v-for="type in productTypes" :key="type.id" :value="type.id">
            {{ type.name }}
          </option>
        </select>
      </div>

      <!-- Название -->
      <div class="form-group">
        <label>Название *</label>
        <input
          v-model="form.name"
          placeholder="Введите название товара"
          required
          class="form-control"
        />
      </div>

      <!-- Стоимость и остаток -->
      <div class="form-row">
        <div class="form-group">
          <label>Стоимость *</label>
          <input
            v-model.number="form.baseCost"
            type="number"
            step="0.01"
            placeholder="Стоимость"
            required
            class="form-control"
          />
        </div>

        <div class="form-group">
          <label>Остаток *</label>
          <input
            v-model.number="form.stock"
            type="number"
            step="0.01"
            placeholder="Остаток"
            disabled
            class="form-control"
          />
          <small class="muted">Остаток рассчитывается автоматически и не редактируется вручную.</small>
        </div>
      </div>

      <!-- Базовая единица измерения -->
      <div class="form-group">
        <label>Базовая единица измерения *</label>
        <select
          v-model.number="form.baseUnitId"
          required
          class="form-control"
        >
          <option value="">Выберите базовую единицу</option>
          <option
            v-for="unit in units"
            :key="unit.id"
            :value="unit.id"
          >
            {{ unitOptionLabel(unit) }}
          </option>
        </select>
      </div>

      <!-- Атрибуты -->
      <div v-for="attr in currentTypeAttributes" :key="attr.id" class="form-group">
        <label>
          {{ attr.name }}
          <span v-if="attr.isRequired" class="required">*</span>
        </label>

        <!-- Число -->
        <input
          v-if="attr.dataType === 'number'"
          v-model.number="form.attributes[attr.code]"
          type="number"
          step="0.01"
          :placeholder="`Введите ${attr.name}`"
          :required="attr.isRequired"
          class="form-control"
        />

        <!-- Строка -->
        <input
          v-else-if="attr.dataType === 'string'"
          v-model="form.attributes[attr.code]"
          type="text"
          :placeholder="`Введите ${attr.name}`"
          :required="attr.isRequired"
          class="form-control"
        />

        <!-- Булево (чекбокс) -->
        <div v-else-if="attr.dataType === 'boolean'" class="form-check">
          <label class="form-check-label">
            <input
              type="checkbox"
              :id="`attr-${attr.code}`"
              v-model="form.attributes[attr.code]"
              class="form-check-input"
            />
            {{ attr.name }}
          </label>
        </div>

        <!-- Если тип неизвестный -->
        <div v-else class="alert alert-warning">
          Неизвестный тип: {{ attr.dataType }}
        </div>
      </div>
      <!-- Флаг составного товара - отображается на основе типа товара -->
      <div class="form-group">
        <label class="form-check-label">
          <input
            type="checkbox"
            :checked="currentProductTypeIsComposite"
            disabled
            class="form-check-input"
          />
          Составной товар (настраивается в типе товара)
        </label>
      </div>

      <!-- Продукто-зависимые единицы измерения -->
      <div id="product-units" class="form-group">
        <label>Привязка юнитов к товару</label>
        <small class="muted">
          По умолчанию можно подставить юниты из типа товара. При строгом режиме типа разрешены только юниты из типа.
        </small>
        <div class="inline-actions">
          <button type="button" class="btn btn-outline btn-sm" :disabled="!currentType" @click="applyTypeUnitsToForm">
            Подставить из типа
          </button>
          <span v-if="currentType?.strictUnitsByType" class="tag tag-warning">Строгий режим юнитов по типу</span>
        </div>
        <div class="product-units-section">
          <div v-for="(pu, index) in form.productUnits" :key="index" class="product-unit-item">
            <div class="form-row">
              <div class="form-group">
                <label>Единица измерения</label>
                <select
                  v-model.number="pu.unit_id"
                  class="form-control"
                >
                  <option value="">Выберите единицу</option>
                  <option v-for="unit in units" :key="unit.id" :value="unit.id">
                    {{ unitOptionLabel(unit) }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>Коэффициент к базовой</label>
                <input
                  v-model.number="pu.ratio_to_base"
                  type="number"
                  step="0.000001"
                  placeholder="Коэффициент"
                  class="form-control"
                />
              </div>

              <div class="form-group">
                <label>Дискретный шаг</label>
                <input
                  v-model.number="pu.discrete_step"
                  type="number"
                  step="0.000001"
                  placeholder="Шаг"
                  class="form-control"
                />
              </div>

              <div class="form-group">
                <label>&nbsp;</label>
                <button type="button" @click="removeProductUnit(index)" class="btn btn-danger btn-sm">Удалить</button>
              </div>
            </div>
          </div>

          <button type="button" @click="addProductUnit" class="btn btn-secondary">+ Добавить единицу</button>
        </div>
      </div>

      <!-- Компоненты (только для составных) -->
      <div v-if="currentProductTypeIsComposite" class="components-section">
        <h3>Компоненты</h3>
        <div v-for="(comp, index) in form.components" :key="index" class="component-item">
          <div class="form-row">
            <div class="form-group">
              <label>Ингредиент</label>
              <select
                v-model="comp.ingredientId"
                class="form-control"
              >
                <option value="">Выберите ингредиент</option>
                <option v-for="p in componentCandidates" :key="p.id" :value="p.id">
                  {{ p.name }} ({{ p.code }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Количество</label>
              <input
                v-model.number="comp.quantity"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="Количество"
                class="form-control"
              />
            </div>

            <div class="form-group">
              <label>&nbsp;</label>
              <button type="button" @click="removeComponent(index)" class="btn btn-danger btn-sm">Удалить</button>
            </div>
          </div>
        </div>
        <button type="button" @click="addComponent" class="btn btn-secondary">+ Добавить компонент</button>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">
          {{ isEditing ? 'Обновить' : 'Создать' }}
        </button>
        <button type="button" @click="cancel" class="btn btn-outline">Отмена</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type {
  ProductType,
  ProductView,
  ProductAttribute,
  ProductComponent as ApiComponent,
  Unit,
  Ingredient
} from '@/api/productApi'
import { productApi } from '@/api/productApi'

// Props and emits
const props = defineProps<{
  productId?: number | null
}>()

const emit = defineEmits(['close', 'saved'])

const router = useRouter()
const route = useRoute()
const isEditing = computed(() => !!props.productId)
const productIdValue = computed(() => (props.productId ? Number(props.productId) : null))

// Состояние
const productTypes = ref<ProductType[]>([])
const ingredients = ref<Ingredient[]>([])
const units = ref<Unit[]>([])  // Add units state
const productView = ref<ProductView | null>(null)
const selectedImageFile = ref<File | null>(null)
const imageUploading = ref(false)
const form = ref({
  productTypeId: 0,
  name: '',
  baseCost: 0,
  stock: 0,
  baseUnitId: 0,  // Add base unit ID
  isComposite: false,  // Add the composite flag to the form
  attributes: {} as Record<string, any>,
  components: [] as Array<{ ingredientId: number; quantity: number }>,
  productUnits: [] as Array<{ unit_id: number; ratio_to_base: number; discrete_step: number | null }>
})

// Вычисляемые свойства
const currentType = computed(() =>
  productTypes.value.find(t => t.id === form.value.productTypeId)
)
const currentTypeAttributes = computed(() => {
  const attrs = currentType.value?.attributes || []
  return [...attrs].sort((a, b) => a.sortOrder - b.sortOrder)
})

// Computed property to determine if the current product type is composite
const currentProductTypeIsComposite = computed(() => {
  // Get the composite flag from the selected product type, not from the form
  const selectedType = productTypes.value.find(t => t.id === form.value.productTypeId);
  return selectedType ? selectedType.isComposite : false;
});

const componentCandidates = computed(() => ingredients.value)

const unitOptionLabel = (unit: Unit) => {
  const description = (unit as any).description ?? (unit as any).name ?? ''
  return description ? `${description} (${unit.code})` : unit.code
}

const unitOptionLabelById = (unitId: number) => {
  const unit = units.value.find((row) => row.id === unitId)
  return unit ? unitOptionLabel(unit) : `#${unitId}`
}

const ensureBaseUnitBinding = () => {
  const baseUnitId = Number(form.value.baseUnitId || 0)
  if (!baseUnitId) return
  const existingIndex = form.value.productUnits.findIndex((row) => Number(row.unit_id) === baseUnitId)
  if (existingIndex >= 0) {
    const existingRow = form.value.productUnits[existingIndex]
    if (existingRow) {
      existingRow.ratio_to_base = 1
      existingRow.discrete_step = null
    }
    return
  }
  form.value.productUnits.unshift({
    unit_id: baseUnitId,
    ratio_to_base: 1,
    discrete_step: null,
  })
}

const applyTypeUnitsToForm = () => {
  const typeUnits = currentType.value?.productTypeUnits || []
  const normalized = typeUnits.map((row: any) => ({
    unit_id: Number(row.unit_id ?? row.unitId ?? 0),
    ratio_to_base: Number(row.ratio_to_base ?? row.ratioToBase ?? 1),
    discrete_step: row.discrete_step ?? row.discreteStep ?? null,
  })).filter((row) => row.unit_id > 0)
  form.value.productUnits = normalized
  ensureBaseUnitBinding()
}

const imageUrl = computed(() => {
  const raw = productView.value?.meta?.image?.trim()
  if (!raw) return ''
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw
  const normalized = raw
    .replace(/^\/app\/public\/images\//, '')
    .replace(/^app\/public\/images\//, '')
    .replace(/^\/+/, '')
  if (normalized.startsWith('images/')) return `/${normalized}`
  return `/images/${normalized}`
})

// Действия
const cancel = () => {
  emit('close')
  if (route.path.startsWith('/product-form')) {
    router.push('/product-list')
  }
}

const onTypeChange = () => {
  form.value.attributes = {}
  // Get the composite flag from the selected product type
  const selectedType = productTypes.value.find(t => t.id === form.value.productTypeId);
  if (selectedType && !selectedType.isComposite) {
    form.value.components = []
  }
  if (!isEditing.value || !form.value.productUnits.length) {
    applyTypeUnitsToForm()
  }
}

const addComponent = () => {
  form.value.components.push({ ingredientId: 0, quantity: 1 })
}

const removeComponent = (index: number) => {
  form.value.components.splice(index, 1)
}

const onImageSelected = (event: Event) => {
  const target = event.target as HTMLInputElement
  selectedImageFile.value = target.files?.[0] ?? null
}

const uploadSelectedImage = async () => {
  if (!productIdValue.value || !selectedImageFile.value) return
  try {
    imageUploading.value = true
    const uploaded = await productApi.uploadProductImage(productIdValue.value, selectedImageFile.value)
    if (!productView.value) {
      productView.value = await productApi.getProductView(productIdValue.value)
    } else {
      const nextMeta = { ...(productView.value.meta ?? {}) }
      nextMeta.image = uploaded.image
      productView.value = { ...productView.value, meta: nextMeta }
    }
    selectedImageFile.value = null
    alert('Фото загружено')
  } catch (e) {
    console.error('Ошибка загрузки фото:', e)
    alert('Не удалось загрузить фото')
  } finally {
    imageUploading.value = false
  }
}

const toInitialAttributes = (product: ProductView, type: ProductType): Record<string, any> => {
  const initialAttributes: Record<string, any> = {}
  for (const def of type.attributes || []) {
    const apiAttr = (product.attributes || []).find(
      (a: ProductAttribute) => a.productAttributeId === def.id
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
  const product = await productApi.getProductView(productId)
  productView.value = product
  const type = productTypes.value.find(t => t.id === product.productTypeId)

  if (!type) {
    alert('Тип товара не найден')
    emit('close')
    return
  }

  const initialComponents = (product.components || []).map((comp: ApiComponent) => ({
    ingredientId: comp.ingredientId,
    quantity: comp.quantity
  }))
  const productType = productTypes.value.find(t => t.id === product.productTypeId)
  const isProductTypeComposite = productType ? productType.isComposite : false
  const productUnits = (product.productUnits || []).map((pu: any) => ({
    unit_id: pu.unit_id ?? pu.unitId ?? 0,
    ratio_to_base: pu.ratio_to_base ?? pu.ratioToBase ?? 1,
    discrete_step: pu.discrete_step ?? pu.discreteStep ?? null
  }))

  form.value = {
    productTypeId: Number(product.productTypeId),
    name: product.name,
    baseCost: product.baseCost,
    stock: product.stock,
    baseUnitId: product.baseUnitId || 0,
    isComposite: isProductTypeComposite,
    attributes: toInitialAttributes(product, type),
    components: isProductTypeComposite ? initialComponents : [],
    productUnits
  }
  ensureBaseUnitBinding()
}

// Сохранение
const handleSubmit = async () => {
  try {
    // Валидация типа
    if (form.value.productTypeId <= 0) {
      alert('Пожалуйста, выберите тип товара')
      return
    }

    // Валидация обязательных атрибутов
    for (const attr of currentTypeAttributes.value) {
      if (attr.isRequired && (form.value.attributes[attr.code] === '' || form.value.attributes[attr.code] == null)) {
        alert(`Обязательное поле: ${attr.name}`)
        return
      }
    }

    // Подготовка payload
    // Get the composite flag from the selected product type
    const selectedType = productTypes.value.find(t => t.id === form.value.productTypeId);
    const isProductTypeComposite = selectedType ? selectedType.isComposite : false;
    if (selectedType?.strictUnitsByType) {
      const allowedUnitIds = new Set<number>((selectedType.productTypeUnits || []).map((row: any) => Number(row.unitId ?? row.unit_id)))
      if (form.value.baseUnitId) allowedUnitIds.add(Number(form.value.baseUnitId))
      const invalidUnit = form.value.productUnits.find((row) => row.unit_id && !allowedUnitIds.has(Number(row.unit_id)))
      if (invalidUnit) {
        alert(`Юнит ${invalidUnit.unit_id} не разрешён типом товара (строгий режим).`)
        return
      }
    }

    const payload: any = {
      product_type_id: form.value.productTypeId,
      name: form.value.name,
      base_cost: form.value.baseCost,
      stock: form.value.stock,
      base_unit_id: form.value.baseUnitId,  // Include base unit ID
      is_composite: isProductTypeComposite,  // Use the composite flag from the product type
      attributes: Object.entries(form.value.attributes)
        .map(([code, value]) => {
          const def = currentType.value?.attributes?.find(a => a.code === code)
          if (!def) return null
          return {
            product_attribute_id: def.id,
            value: String(value) // всегда строка для бэкенда
          }
        })
        .filter(Boolean) as Array<{ product_attribute_id: number; value: string }>,
      components: isProductTypeComposite  // Use the composite flag from the product type
        ? form.value.components.map(c => ({
            ingredient_id: c.ingredientId,
            quantity: c.quantity
          }))
        : []
    }

    if (isEditing.value && props.productId) {
      // Pass the updated form data with isComposite field
      await productApi.updateProduct(props.productId, {
        ...form.value,
        isComposite: form.value.isComposite
      })
      await loadProductForEdit(Number(props.productId))
      alert('Товар обновлён!')
    } else {
      // Pass the form data with isComposite field
      await productApi.createProduct({
        ...form.value,
        isComposite: form.value.isComposite
      })
      alert('Товар создан!')
    }
    emit('saved')
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert('Ошибка при сохранении товара')
  }
}

// Загрузка данных
onMounted(async () => {
  try {
    const [typesRes, unitsRes, ingredientsRes] = await Promise.all([
      productApi.getProductTypes(),
      productApi.getUnits(),
      productApi.getIngredients(),
    ])

    units.value = unitsRes
    productTypes.value = typesRes.map(type => ({
      ...type,
      attributes: type.attributes?.map(attr => ({
        ...attr,
        dataType: (attr as any).data_type || attr.dataType
      })) || [],
      productTypeUnits: (type.productTypeUnits || []).map((row: any) => ({
        ...row,
        unitId: row.unitId ?? row.unit_id,
        ratioToBase: row.ratioToBase ?? row.ratio_to_base,
        discreteStep: row.discreteStep ?? row.discrete_step ?? null,
      })),
    }))
    ingredients.value = ingredientsRes

    if (isEditing.value && props.productId) {
      await loadProductForEdit(Number(props.productId))
    } else {
      form.value = {
        productTypeId: 0,
        name: '',
        baseCost: 0,
        stock: 0,
        baseUnitId: 0,
        isComposite: false,
        attributes: {},
        components: [],
        productUnits: []
      }
      productView.value = null
    }
  } catch (e) {
    console.error('Ошибка загрузки данных:', e)
    alert('Не удалось загрузить данные товара')
    emit('close')
  }
})

// Watch for changes in props.productId to reload data when editing different products
watch(() => props.productId, async (newId) => {
  if (newId) {
    try {
      await loadProductForEdit(Number(newId))
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
      alert('Не удалось загрузить данные товара')
      emit('close')
    }
  } else {
    productView.value = null
  }
})

watch(
  () => form.value.baseUnitId,
  () => {
    ensureBaseUnitBinding()
  }
)

// Methods for managing product-specific units
const addProductUnit = () => {
  form.value.productUnits.push({
    unit_id: 0,
    ratio_to_base: 1.0,
    discrete_step: null
  });
};

const removeProductUnit = (index: number) => {
  const row = form.value.productUnits[index]
  if (row && Number(row.unit_id) === Number(form.value.baseUnitId)) {
    alert('Базовую единицу нельзя удалить из привязки.')
    return
  }
  form.value.productUnits.splice(index, 1);
};
</script>

<style scoped>
.product-form-container {
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.head-actions {
  display: flex;
  gap: 8px;
}

.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
}

.meta {
  display: grid;
  gap: 6px;
}

.units-summary {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
}

.units-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.anchor-link {
  color: #2563eb;
  text-decoration: none;
}

.units-summary-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.unit-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
}

.image-wrap {
  max-width: 460px;
  margin-bottom: 10px;
}

.product-image {
  width: 100%;
  max-height: 380px;
  object-fit: contain;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.upload-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.muted {
  color: #6b7280;
}

.form-group {
  margin-bottom: 15px;
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-row .form-group {
  flex: 1;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-check {
  display: flex;
  align-items: center;
}

.form-check-input {
  margin-right: 8px;
}

.form-check-label {
  display: flex;
  align-items: center;
}

.product-units-section {
  border: 1px solid #ddd;
  padding: 15px;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.inline-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 10px;
}

.tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
}

.tag-warning {
  background: #fff7ed;
  color: #9a3412;
}

.product-unit-item {
  margin-bottom: 10px;
  padding: 10px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #eee;
}

.required {
  color: red;
}

.components-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 4px;
  background-color: #fafafa;
}

.component-item {
  margin-bottom: 10px;
  padding: 10px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #eee;
}

.alert {
  padding: 10px;
  border-radius: 4px;
  margin-top: 5px;
}

.alert-warning {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.btn {
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  text-align: center;
  margin-right: 5px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-outline {
  background-color: transparent;
  border: 1px solid #6c757d;
  color: #6c757d;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.form-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

@media (max-width: 1024px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
  .upload-controls {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
