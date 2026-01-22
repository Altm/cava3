<template>
  <div>
    <h2>{{ isEditing ? 'Редактировать товар' : 'Создать товар' }}</h2>
    <form @submit.prevent="handleSubmit">
      <!-- Тип товара -->
      <label>
        Тип:
        <select v-model="form.productTypeId" @change="onTypeChange" :disabled="isEditing">
          <option value="">Выберите тип</option>
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
import type { ProductType, Product } from '@/api/productApi'
import { productApi } from '@/api/productApi'

const route = useRoute()
const router = useRouter()
const productId = computed(() => route.params.id as string | undefined)
const isEditing = computed(() => !!productId.value)

const productTypes = ref<ProductType[]>([])
const simpleProducts = ref<Product[]>([])
const form = ref({
  productTypeId: 0,
  name: '',
  unitCost: 0,
  stock: 0,
  attributes: {} as Record<string, any>,
  components: [] as Array<{ componentProductId: number; quantity: number }>
})

const currentType = computed(() =>
  productTypes.value.find(t => t.id === form.value.productTypeId)
)
const currentTypeAttributes = computed(() => currentType.value?.attributes || [])
const isComposite = computed(() => currentType.value?.isComposite || false)

const cancel = () => {
  router.push('/')
}

const onTypeChange = () => {
  form.value.attributes = {}
}

const addComponent = () => {
  form.value.components.push({ componentProductId: 0, quantity: 1 })
}

const removeComponent = (index: number) => {
  form.value.components.splice(index, 1)
}

const handleCheckboxChange = (event: Event, code: string) => {
  const target = event.target as HTMLInputElement;
  form.value.attributes[code] = target.checked;
}

const handleSubmit = async () => {
  try {
    if (isEditing.value && productId.value) {
      // Update existing product
      await productApi.updateProduct(parseInt(productId.value), form.value)
      alert('Товар обновлен!')
    } else {
      // Create new product
      await productApi.createProduct(form.value)
      alert('Товар создан!')
    }
    router.push('/')
  } catch (e) {
    console.error(e)
    alert('Ошибка при сохранении товара')
  }
}

onMounted(async () => {
  const productTypesRaw = await productApi.getProductTypes()
  const simpleProductsRaw = await productApi.getProducts()
//TODO:Заменить на беке START
  productTypes.value = productTypesRaw.map(type => ({
    ...type,
    attributes: type.attributes?.map(attr => ({
      ...attr,
      dataType: (attr as any).data_type // ← вот сюда вставили 2-й вариант
    }))
  }))
//TODO:Заменить на беке END

  if (isEditing.value && productId.value) {
    // Загружаем данные товара
    const productData = await productApi.getProduct(parseInt(productId.value))

    // Находим тип товара
    const productType = productTypes.value.find(pt => pt.id === productData.product_type_id)

    // Инициализируем атрибуты ТОЛЬКО внутри этого блока
    const initialAttributes: Record<string, any> = {}

    if (productType?.attributes) {
      for (const attr of productType.attributes) {
        // Используем данные из API или дефолт
        const apiValue = productData.attributes?.[attr.code]
        if (apiValue !== undefined && apiValue !== null) {
          initialAttributes[attr.code] = apiValue
        } else {
          // Дефолтные значения по типу
          switch (attr.dataType) {
            case 'number': initialAttributes[attr.code] = 0; break
            case 'boolean': initialAttributes[attr.code] = false; break
            case 'string': initialAttributes[attr.code] = ''; break
            default: initialAttributes[attr.code] = null
          }
        }
      }
    }

    // Устанавливаем форму
    form.value = {
      productTypeId: productData.product_type_id,
      name: productData.name,
      unitCost: productData.unit_cost,
      stock: productData.stock,
      attributes: initialAttributes,
      components: productData.components || []
    }
  } else {
    // Новый товар
    form.value.attributes = {}
  }
})
</script>

<style scoped>
.required {
  color: red;
}
</style>
