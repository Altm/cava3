<template>
  <div>
    <h2>Продажа товаров</h2>
    <form @submit.prevent="handleSale">
      <div>
        <label>Товар:</label>
        <select v-model="saleForm.productId" required>
          <option value="">Выберите товар</option>
          <option v-for="product in products" :key="product.id" :value="product.id">
            {{ product.name }} (остаток: {{ product.stock }})
          </option>
        </select>
      </div>

      <div>
        <label>Количество:</label>
        <input 
          v-model.number="saleForm.quantity" 
          type="number" 
          min="0.01" 
          step="0.01" 
          placeholder="Количество" 
          required 
        />
      </div>

      <button type="submit" :disabled="!saleForm.productId || saleForm.quantity <= 0">
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
import { ref, onMounted } from 'vue'
import type { Product } from '@/api/productApi'
import { productApi } from '@/api/productApi'

interface SaleForm {
  productId: number | null
  quantity: number
}

interface SaleResult {
  message: string
  total_cost: number
}

const saleForm = ref<SaleForm>({
  productId: null,
  quantity: 1
})

const products = ref<Product[]>([])
const saleResult = ref<SaleResult | null>(null)

const handleSale = async () => {
  try {
    const response = await fetch('/api/sales/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        product_id: saleForm.value.productId,
        quantity: saleForm.value.quantity
      })
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
    saleForm.value = { productId: null, quantity: 1 }
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