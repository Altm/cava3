<template>
  <div>
    <h2>Список товаров</h2>
    <router-link to="/product-form">Создать товар</router-link>
    <div v-if="loading">Загрузка...</div>
    <div v-else>
      <div v-for="product in products" :key="product.id" class="product-item">
        <h3>{{ product.name }}</h3>
        <p>Тип: {{ getProductTypeName(product.product_type_id) }}</p>
        <p>Остаток: {{ product.stock }}</p>
        <p>Себестоимость: {{ product.unit_cost }}</p>
        <p v-if="product.is_composite">Составной товар</p>
        <div v-if="Object.keys(product.attributes).length > 0">
          <h4>Атрибуты:</h4>
          <ul>
            <li v-for="(value, key) in product.attributes" :key="key">
              {{ key }}: {{ value }}
            </li>
          </ul>
        </div>
        <div v-if="product.components && product.components.length > 0">
          <h4>Компоненты:</h4>
          <ul>
            <li v-for="comp in product.components" :key="`${product.id}-${comp.componentProductId}`">
              Товар ID: {{ comp.componentProductId }}, Количество: {{ comp.quantity }}
            </li>
          </ul>
        </div>
        <div>
          <button @click="editProduct(product.id)">Редактировать</button>
          <button @click="deleteProduct(product.id)">Удалить</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { productApi, Product, ProductType } from '@/api/productApi'

const router = useRouter()
const products = ref<Product[]>([])
const productTypes = ref<ProductType[]>([])
const loading = ref(true)

const loadProducts = async () => {
  try {
    loading.value = true
    products.value = await productApi.getProducts()
  } catch (error) {
    console.error('Error loading products:', error)
  } finally {
    loading.value = false
  }
}

const loadProductTypes = async () => {
  try {
    productTypes.value = await productApi.getProductTypes()
  } catch (error) {
    console.error('Error loading product types:', error)
  }
}

const getProductTypeName = (productTypeId: number) => {
  const productType = productTypes.value.find(pt => pt.id === productTypeId)
  return productType ? productType.name : 'Неизвестный тип'
}

const editProduct = (productId: number) => {
  router.push(`/product-form/${productId}`)
}

const deleteProduct = async (productId: number) => {
  if (confirm('Вы уверены, что хотите удалить этот товар?')) {
    try {
      await productApi.deleteProduct(productId)
      await loadProducts() // Refresh the list
    } catch (error) {
      console.error('Error deleting product:', error)
      alert('Ошибка при удалении товара')
    }
  }
}

onMounted(async () => {
  await Promise.all([
    loadProducts(),
    loadProductTypes()
  ])
})
</script>

<style scoped>
.product-item {
  border: 1px solid #ccc;
  margin: 10px;
  padding: 10px;
  border-radius: 4px;
}

.product-item h3 {
  margin-top: 0;
}
</style>