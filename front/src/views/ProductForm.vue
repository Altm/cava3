<template>
  <div class="product-form-container">
    <h2>{{ isEditing ? 'Редактировать товар' : 'Создать товар' }}</h2>

    <form @submit.prevent="handleSubmit" class="product-form">
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

      <!-- Себестоимость и остаток -->
      <div class="form-row">
        <div class="form-group">
          <label>Себестоимость *</label>
          <input
            v-model.number="form.unitCost"
            type="number"
            step="0.01"
            placeholder="Себестоимость"
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
            required
            class="form-control"
          />
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
            {{ unit.name }} ({{ unit.code }})
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
      <div class="form-group">
        <label>Продукто-зависимые единицы измерения</label>
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
                    {{ unit.name }} ({{ unit.code }})
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
              <label>Компонент</label>
              <select
                v-model="comp.componentProductId"
                class="form-control"
              >
                <option value="">Выберите компонент</option>
                <option v-for="p in simpleProducts" :key="p.id" :value="p.id">
                  {{ p.name }}
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
import { useRouter } from 'vue-router'
import type {
  ProductType,
  Product,
  ProductAttribute,
  ProductComponent as ApiComponent,
  Unit
} from '@/api/productApi'
import { productApi } from '@/api/productApi'

// Props and emits
const props = defineProps<{
  productId?: number | null
}>()

const emit = defineEmits(['close', 'saved'])

const router = useRouter()
const isEditing = computed(() => !!props.productId)

// Состояние
const productTypes = ref<ProductType[]>([])
const allProducts = ref<Product[]>([])
const units = ref<Unit[]>([])  // Add units state
const form = ref({
  productTypeId: 0,
  name: '',
  unitCost: 0,
  stock: 0,
  baseUnitId: 0,  // Add base unit ID
  isComposite: false,  // Add the composite flag to the form
  attributes: {} as Record<string, any>,
  components: [] as Array<{ componentProductId: number; quantity: number }>,
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

const simpleProducts = computed(() =>
  allProducts.value.filter(p => !p.isComposite)
)

// Действия
const cancel = () => emit('close')

const onTypeChange = () => {
  form.value.attributes = {}
  // Get the composite flag from the selected product type
  const selectedType = productTypes.value.find(t => t.id === form.value.productTypeId);
  if (selectedType && !selectedType.isComposite) {
    form.value.components = []
  }
}

const addComponent = () => {
  form.value.components.push({ componentProductId: 0, quantity: 1 })
}

const removeComponent = (index: number) => {
  form.value.components.splice(index, 1)
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

    const payload: any = {
      product_type_id: form.value.productTypeId,
      name: form.value.name,
      unit_cost: form.value.unitCost,
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
        .filter(Boolean) as ApiAttribute[],
      components: isProductTypeComposite  // Use the composite flag from the product type
        ? form.value.components.map(c => ({
            component_product_id: c.componentProductId,
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
    // Загружаем типы, все товары и единицы измерения параллельно
    const [typesRes, productsRes, unitsRes] = await Promise.all([
      productApi.getProductTypes(),
      productApi.getProducts(),
      productApi.getUnits()  // Load units
    ])

    units.value = unitsRes  // Store units

    // Нормализуем типы (если нужно — см. ваш TODO)
    productTypes.value = typesRes.map(type => ({
      ...type,
      attributes: type.attributes?.map(attr => ({
        ...attr,
        dataType: (attr as any).data_type || attr.dataType
      })) || []
    }))

    allProducts.value = productsRes

    if (isEditing.value && props.productId) {
      const product = await productApi.getProduct(props.productId)
      const type = productTypes.value.find(t => t.id === product.productTypeId)

      if (!type) {
        alert('Тип товара не найден')
        emit('close')
        return
      }

      // Преобразуем атрибуты из массива в объект { code: value }
      const initialAttributes: Record<string, any> = {}
      if (type.attributes) {
        for (const def of type.attributes) {
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
            // Дефолтные значения
            value = def.dataType === 'number' ? 0 : def.dataType === 'boolean' ? false : ''
          }
          initialAttributes[def.code] = value
        }
      }

      // Преобразуем компоненты
      const initialComponents = (product.components || []).map((comp: ApiComponent) => ({
        componentProductId: comp.componentProductId,
        quantity: comp.quantity
      }))

      // Get the composite flag from the product type
      const productType = productTypes.value.find(t => t.id === product.productTypeId);
      const isProductTypeComposite = productType ? productType.isComposite : false;

      // Get product-specific units if available
      const productUnits = product.productUnits || [];

      // Устанавливаем форму
      form.value = {
        productTypeId: Number(product.productTypeId), // ← гарантируем number
        name: product.name,
        unitCost: product.unitCost,
        stock: product.stock,
        baseUnitId: product.baseUnitId || 0,  // Set base unit ID
        isComposite: isProductTypeComposite,  // Use the composite flag from the product type
        attributes: initialAttributes,
        components: isProductTypeComposite ? initialComponents : [],  // Only include components if product type is composite
        productUnits: productUnits  // Add product-specific units
      }
    } else {
      // Новый товар — начальное состояние
      form.value = {
        productTypeId: 0,
        name: '',
        unitCost: 0,
        stock: 0,
        baseUnitId: 0,  // Default base unit ID
        isComposite: false,  // Default to non-composite for new products
        attributes: {},
        components: [],
        productUnits: []  // Initialize with empty product units
      }
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
    // Reload data for the new product ID
    try {
      const product = await productApi.getProduct(newId)
      const type = productTypes.value.find(t => t.id === product.productTypeId)

      if (!type) {
        alert('Тип товара не найден')
        emit('close')
        return
      }

      // Преобразуем атрибуты из массива в объект { code: value }
      const initialAttributes: Record<string, any> = {}
      if (type.attributes) {
        for (const def of type.attributes) {
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
            // Дефолтные значения
            value = def.dataType === 'number' ? 0 : def.dataType === 'boolean' ? false : ''
          }
          initialAttributes[def.code] = value
        }
      }

      // Преобразуем компоненты
      const initialComponents = (product.components || []).map((comp: ApiComponent) => ({
        componentProductId: comp.componentProductId,
        quantity: comp.quantity
      }))

      // Get the composite flag from the product type
      const productType = productTypes.value.find(t => t.id === product.productTypeId);
      const isProductTypeComposite = productType ? productType.isComposite : false;

      // Устанавливаем форму
      form.value = {
        productTypeId: Number(product.productTypeId), // ← гарантируем number
        name: product.name,
        unitCost: product.unitCost,
        stock: product.stock,
        baseUnitId: product.baseUnitId || 0,  // Set base unit ID
        isComposite: isProductTypeComposite,  // Use the composite flag from the product type
        attributes: initialAttributes,
        components: isProductTypeComposite ? initialComponents : [],  // Only include components if product type is composite
        productUnits: productUnits  // Add product-specific units
      }
    } catch (e) {
      console.error('Ошибка загрузки данных:', e)
      alert('Не удалось загрузить данные товара')
      emit('close')
    }
  }
})

// Methods for managing product-specific units
const addProductUnit = () => {
  form.value.productUnits.push({
    unit_id: 0,
    ratio_to_base: 1.0,
    discrete_step: null
  });
};

const removeProductUnit = (index: number) => {
  form.value.productUnits.splice(index, 1);
};
</script>

<style scoped>
.product-form-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
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
</style>
