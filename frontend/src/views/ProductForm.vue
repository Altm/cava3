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
      <div v-for="attr in currentTypeAttributes" :key="attr.id">
        <label>{{ attr.name }} <span v-if="attr.isRequired" class="required">*</span></label>
        <input
          v-if="attr.dataType === 'number'"
          v-model.number="form.attributes[attr.code]"
          type="number"
          :placeholder="attr.name"
        />
        <input
          v-else-if="attr.dataType === 'string'"
          v-model="form.attributes[attr.code]"
          type="text"
          :placeholder="attr.name"
        />
        <input
          v-else-if="attr.dataType === 'boolean'"
          v-model="form.attributes[attr.code]"
          type="checkbox"
        />
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
import { productApi, ProductType, Product } from '@/api/productApi'

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
  productTypes.value = await productApi.getProductTypes()
  // Load all products to use as components for composite products
  simpleProducts.value = await productApi.getProducts()
  
  if (isEditing.value && productId.value) {
    // Load existing product data for editing
    const productData = await productApi.getProduct(parseInt(productId.value))
    
    form.value = {
      productTypeId: productData.product_type_id,
      name: productData.name,
      unitCost: productData.unit_cost,
      stock: productData.stock,
      attributes: productData.attributes,
      components: productData.components || []
    }
  }
})
</script>

<style scoped>
.required {
  color: red;
}
</style>
</template>