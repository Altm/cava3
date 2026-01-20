<template>
  <div>
    <h2>Создать товар</h2>
    <form @submit.prevent="handleSubmit">
      <!-- Тип товара -->
      <label>
        Тип:
        <select v-model="form.productTypeId" @change="onTypeChange">
          <option v-for="type in productTypes" :key="type.id" :value="type.id">
            {{ type.name }}
          </option>
        </select>
      </label>

      <!-- Название -->
      <input v-model="form.name" placeholder="Название" required />

      <!-- Себестоимость и остаток -->
      <input v-model.number="form.unitCost" type="number" placeholder="Себестоимость" />
      <input v-model.number="form.stock" type="number" placeholder="Остаток" />

      <!-- Атрибуты -->
      <div v-for="attr in currentTypeAttributes" :key="attr.id">
        <label>{{ attr.name }}</label>
        <input
          v-if="attr.dataType === 'number'"
          v-model.number="form.attributes[attr.code]"
          type="number"
        />
        <input
          v-else-if="attr.dataType === 'string'"
          v-model="form.attributes[attr.code]"
          type="text"
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
            <option v-for="p in simpleProducts" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
          <input v-model.number="comp.quantity" type="number" placeholder="Количество" />
          <button type="button" @click="removeComponent(index)">Удалить</button>
        </div>
        <button type="button" @click="addComponent">+ Добавить компонент</button>
      </div>

      <button type="submit">Сохранить</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { productApi, ProductType } from '@/api/productApi'

const productTypes = ref<ProductType[]>([])
const simpleProducts = ref<any[]>([]) // можно загрузить отдельно
const form = ref({
  productTypeId: 1,
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

const onTypeChange = () => {
  form.value.attributes = {}
}

const addComponent = () => {
  form.value.components.push({ componentProductId: 1, quantity: 1 })
}

const removeComponent = (index: number) => {
  form.value.components.splice(index, 1)
}

const handleSubmit = async () => {
  try {
    await productApi.createProduct(form.value)
    alert('Товар создан!')
  } catch (e) {
    console.error(e)
    alert('Ошибка')
  }
}

onMounted(async () => {
  productTypes.value = await productApi.getProductTypes()
  // Загрузить простые товары для компонентов
})
</script>