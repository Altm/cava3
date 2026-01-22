<template>
  <div>
    <h2>Продажа товаров</h2>
    <form @submit.prevent="handleSale">
      <div>
        <label>Товар:</label>
        <select v-model="saleForm.productId" @change="onProductChange" required>
          <option value="">Выберите товар</option>
          <option v-for="product in products" :key="product.id" :value="product.id">
            {{ product.name }} (остаток: {{ product.stock }}) {{ getGlassesPerBottleText(product) }}
          </option>
        </select>
      </div>

      <div>
        <label>Тип продажи:</label>
        <select v-model="saleForm.saleType" required>
          <option value="full">Полная продажа</option>
          <option value="glass" v-if="currentProductHasGlasses">Продажа бокалов</option>
        </select>
      </div>

      <div>
        <label>Количество:</label>
        <input 
          v-model.number="saleForm.quantity" 
          type="number" 
          min="0.01" 
          step="0.01" 
          :placeholder="getQuantityPlaceholder" 
          required 
        />
        <small v-if="currentProductHasGlasses && saleForm.saleType === 'glass'">
          1 бокал = {{ glassesPerBottle ? (1 / glassesPerBottle).toFixed(4) : '?' }} бутылки
        </small>
      </div>

      <button type="submit" :disabled="!canSubmit">
        Продать
      </button>
    </form>

    <div v-if="saleResult" class="result">
      <h3>Результат продажи:</h3>
      <p>{{ saleResult.message }}</p>
      <p><strong>Общая стоимость:</strong> {{ saleResult.total_cost }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Product } from '@/api/productApi'
import { productApi } from '@/api/productApi'

interface SaleForm {
  productId: number | null
  quantity: number
  saleType: 'full' | 'glass'
}

interface SaleResult {
  message: string
  total_cost: number
}

const saleForm = ref<SaleForm>({
  productId: null,
  quantity: 1,
  saleType: 'full'
})

const products = ref<Product[]>([])
const saleResult = ref<SaleResult | null>(null)
const glassesPerBottle = ref<number | null>(null)

const currentProductHasGlasses = computed(() => {
  if (!saleForm.value.productId) return false
  const product = products.value.find(p => p.id === saleForm.value.productId)
  return product && product.attributes && typeof product.attributes.glasses_per_bottle !== 'undefined' && product.attributes.glasses_per_bottle !== null
})

const canSubmit = computed(() => {
  return saleForm.value.productId !== null && 
         saleForm.value.quantity > 0 &&
         (!currentProductHasGlasses.value || saleForm.value.saleType !== 'glass' || glassesPerBottle.value !== null)
})

const getQuantityPlaceholder = computed(() => {
  if (saleForm.value.saleType === 'glass' && currentProductHasGlasses.value) {
    return 'Количество бокалов'
  }
  return 'Количество'
})

const getGlassesPerBottleText = (product: Product) => {
  if (product.attributes && product.attributes.glasses_per_bottle) {
    return `(бокалов в бутылке: ${product.attributes.glasses_per_bottle})`
  }
  return ''
}

const onProductChange = () => {
  if (saleForm.value.productId) {
    const product = products.value.find(p => p.id === saleForm.value.productId)
    if (product && product.attributes && product.attributes.glasses_per_bottle) {
      glassesPerBottle.value = product.attributes.glasses_per_bottle
      if (!currentProductHasGlasses.value) {
        saleForm.value.saleType = 'full'
      }
    } else {
      glassesPerBottle.value = null
      saleForm.value.saleType = 'full'
    }
  }
}

const handleSale = async () => {
  try {
    let url = '/api/sales/'
    let requestBody = {
      product_id: saleForm.value.productId,
      quantity: saleForm.value.quantity
    }

    if (saleForm.value.saleType === 'glass') {
      url = '/api/glass-sales/'
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Ошибка при продаже товара')
    }

    const result = await response.json()
    saleResult.value = result
    // Refresh products list
    loadProducts()
    // Reset form
    saleForm.value = { productId: null, quantity: 1, saleType: 'full' }
    glassesPerBottle.value = null
  } catch (error) {
    console.error('Ошибка при продаже:', error)
    alert(error instanceof Error ? error.message : 'Ошибка при продаже товара')
  }
}

const loadProducts = async () => {
  try {
    products.value = await productApi.getProducts()
  } catch (error) {
    console.error('Ошибка при загрузке товаров:', error)
  }
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 400px;
  margin-bottom: 2rem;
}

form > div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.result {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #f5f5f5;
}
</style>