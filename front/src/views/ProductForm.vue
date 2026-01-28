<template>
  <div>
    <h2>{{ isEditing ? 'Редактировать товар' : 'Создать товар' }}</h2>
    <form @submit.prevent="handleSubmit">
      <!-- Тип товара -->
      <label>
        Тип:
      <select v-model.number="form.productTypeId" required @change="onTypeChange" :disabled="isEditing">
        <option :value="null">Выберите тип</option>
        <option v-for="type in productTypes" :key="type.id" :value="type.id">
          {{ type.name }}
        </option>
      </select>
      </label>

      <!-- Название -->
      <input v-model="form.name" placeholder="Название" required />

      <!-- Себестоимость и остаток -->
      <input v-model.number="form.unitCost" type="number" placeholder="Себестоимость" required />
      <input v-model.number="form.stock" type="number" placeholder="Остаток" required />

      <!-- Атрибуты -->
      <!--<pre>{{ currentTypeAttributes }}</pre>-->
      <div v-for="attr in currentTypeAttributes" :key="attr.id">
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
          class="attribute-input"
        />

        <!-- Строка -->
        <input
          v-else-if="attr.dataType === 'string'"
          v-model="form.attributes[attr.code]"
          type="text"
          :placeholder="`Введите ${attr.name}`"
          :required="attr.isRequired"
          class="attribute-input"
        />

        <!-- Булево (чекбокс) -->
        <div v-else-if="attr.dataType === 'boolean'" style="display: flex; align-items: center; gap: 8px;">
          <input
            type="checkbox"
            :id="`attr-${attr.code}`"
            :checked="!!form.attributes[attr.code]"
            @change="(e) => form.attributes[attr.code] = (e.target as HTMLInputElement).checked"
          />
          <label :for="`attr-${attr.code}`">Да</label>
        </div>

        <!-- Если тип неизвестный -->
        <div v-else>
          <span>Неизвестный тип: {{ attr.dataType }}</span>
        </div>
      </div>

      <!-- Компоненты (только для составных) -->
      <div v-if="isComposite">
        <h3>Компоненты</h3>
        <div v-for="(comp, index) in form.components" :key="index">
          <select v-model="comp.componentProductId">
            <option value="">Выберите компонент</option>
            <option v-for="p in simpleProducts" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
          <input v-model.number="comp.quantity" type="number" placeholder="Количество" />
          <button type="button" @click="removeComponent(index)">Удалить</button>
        </div>
        <button type="button" @click="addComponent">+ Добавить компонент</button>
      </div>

      <button type="submit">{{ isEditing ? 'Обновить' : 'Создать' }}</button>
      <button type="button" @click="cancel">Отмена</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type {
  ProductType,
  Product,
  ProductAttributeValue as ApiAttribute,
  ProductComponent as ApiComponent
} from '@/api/productApi'
import { productApi } from '@/api/productApi'

const route = useRoute()
const router = useRouter()
const productId = computed(() => route.params.id as string | undefined)
const isEditing = computed(() => !!productId.value)

// Состояние
const productTypes = ref<ProductType[]>([])
const allProducts = ref<Product[]>([])
const form = ref({
  productTypeId: 0,
  name: '',
  unitCost: 0,
  stock: 0,
  attributes: {} as Record<string, any>,
  components: [] as Array<{ componentProductId: number; quantity: number }>
})

// Вычисляемые свойства
const currentType = computed(() =>
  productTypes.value.find(t => t.id === form.value.productTypeId)
)
const currentTypeAttributes = computed(() => currentType.value?.attributes || [])
const isComposite = computed(() => currentType.value?.isComposite || false)
const simpleProducts = computed(() =>
  allProducts.value.filter(p => !p.is_composite)
)

// Действия
const cancel = () => router.push('/')

const onTypeChange = () => {
  form.value.attributes = {}
  if (!isComposite.value) {
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

    console.log('RAW productTypeId:', form.value.productTypeId)
    console.log('AFTER Number():', Number(form.value.productTypeId))
    console.log('typeof RAW:', typeof form.value.productTypeId)

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
    const payload: any = {
      product_type_id: form.value.productTypeId,
      name: form.value.name,
      unit_cost: form.value.unitCost,
      stock: form.value.stock,
      attributes: Object.entries(form.value.attributes)
        .map(([code, value]) => {
          const def = currentType.value?.attributes?.find(a => a.code === code)
          if (!def) return null
          return {
            attribute_definition_id: def.id,
            value: String(value) // всегда строка для бэкенда
          }
        })
        .filter(Boolean) as ApiAttribute[],
      components: isComposite.value
        ? form.value.components.map(c => ({
            component_product_id: c.componentProductId,
            quantity: c.quantity
          }))
        : []
    }

    if (isEditing.value && productId.value) {
      await productApi.updateProduct(Number(route.params.id), form.value)
      alert('Товар обновлён!')
    } else {
      await productApi.createProduct(form.value)
      alert('Товар создан!')
    }
    router.push('/')
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert('Ошибка при сохранении товара')
  }
}

// Загрузка данных
onMounted(async () => {
  try {
    // Загружаем типы и все товары параллельно
    const [typesRes, productsRes] = await Promise.all([
      productApi.getProductTypes(),
      productApi.getProducts()
    ])

    // Нормализуем типы (если нужно — см. ваш TODO)
    productTypes.value = typesRes.map(type => ({
      ...type,
      attributes: type.attributes?.map(attr => ({
        ...attr,
        dataType: (attr as any).data_type || attr.dataType
      })) || []
    }))

    allProducts.value = productsRes

    if (isEditing.value && productId.value) {
      const product = await productApi.getProduct(Number(productId.value))
      const type = productTypes.value.find(t => t.id === product.product_type_id)

      if (!type) {
        alert('Тип товара не найден')
        router.push('/')
        return
      }

      // Преобразуем атрибуты из массива в объект { code: value }
      const initialAttributes: Record<string, any> = {}
      if (type.attributes) {
        for (const def of type.attributes) {
          const apiAttr = (product.attributes || []).find(
            (a: ApiAttribute) => a.attribute_definition_id === def.id
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
        componentProductId: comp.component_product_id,
        quantity: comp.quantity
      }))

      // Устанавливаем форму
      form.value = {
        productTypeId: Number(product.product_type_id), // ← гарантируем number
        name: product.name,
        unitCost: product.unit_cost,
        stock: product.stock,
        attributes: initialAttributes,
        components: initialComponents
      }
    } else {
      // Новый товар — начальное состояние
      form.value = {
        productTypeId: 0,
        name: '',
        unitCost: 0,
        stock: 0,
        attributes: {},
        components: []
      }
    }
  } catch (e) {
    console.error('Ошибка загрузки данных:', e)
    alert('Не удалось загрузить данные товара')
    router.push('/')
  }
})
</script>

<style scoped>
.required {
  color: red;
}
.attribute-input {
  width: 20%;
  padding: 4px;
  margin: 4px 0;
}
</style>
