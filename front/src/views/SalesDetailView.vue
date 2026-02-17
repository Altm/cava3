<template>
  <div class="page">
    <div class="page-head">
      <h2>Продажа #{{ saleId }}</h2>
      <div class="actions">
        <RouterLink class="btn btn-outline" to="/sales/list">К списку продаж</RouterLink>
        <button
          v-if="sale?.status === 'pending'"
          class="btn btn-primary"
          :disabled="confirming"
          @click="confirmSale"
        >
          {{ confirming ? 'Подтверждение...' : 'Подтвердить продажу' }}
        </button>
      </div>
    </div>

    <div class="card" v-if="sale">
      <div class="meta-grid">
        <div><b>ID:</b> {{ sale.id }}</div>
        <div><b>Sale ID:</b> {{ sale.saleId ?? '-' }}</div>
        <div><b>Статус:</b> {{ sale.status }}</div>
        <div><b>Terminal:</b> {{ sale.terminalId ?? '-' }}</div>
        <div><b>Локация:</b> {{ sale.locationName ?? sale.locationId }}</div>
        <div><b>User ID:</b> {{ sale.userId ?? '-' }}</div>
        <div><b>Сумма:</b> {{ sale.totalAmount }}</div>
        <div><b>Создано:</b> {{ formatDate(sale.createdAt) }}</div>
        <div><b>Подтверждено:</b> {{ formatDate(sale.confirmedAt) }}</div>
      </div>
    </div>

    <div class="card" v-if="sale">
      <h3>Содержимое продажи</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Товар</th>
              <th>SKU</th>
              <th>Количество</th>
              <th>Юнит</th>
              <th>Валюта</th>
              <th>Сумма строки</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in sale.lines" :key="line.id">
              <td>{{ line.id }}</td>
              <td>{{ line.productName }}</td>
              <td>{{ line.productSku ?? '-' }}</td>
              <td>{{ line.quantity }}</td>
              <td>{{ line.unitCode }}</td>
              <td>{{ line.currency }}</td>
              <td>{{ line.lineTotalAmount }}</td>
            </tr>
            <tr v-if="!sale.lines.length">
              <td colspan="7">Нет строк продажи</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" v-if="sale">
      <h3>Payload</h3>
      <pre class="payload">{{ prettyPayload }}</pre>
    </div>

    <div class="card" v-if="loading">Загрузка...</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type SaleDetail } from '@/api/productApi'

const route = useRoute()
const saleId = Number(route.params.id)
const sale = ref<SaleDetail | null>(null)
const loading = ref(false)
const confirming = ref(false)

const prettyPayload = computed(() => JSON.stringify(sale.value?.payload ?? {}, null, 2))

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const loadSale = async () => {
  try {
    loading.value = true
    sale.value = await productApi.getSale(saleId)
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки продажи')
  } finally {
    loading.value = false
  }
}

const confirmSale = async () => {
  if (!sale.value || sale.value.status === 'confirmed' || confirming.value) return
  try {
    confirming.value = true
    sale.value = await productApi.confirmSale(sale.value.id)
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка подтверждения продажи')
  } finally {
    confirming.value = false
  }
}

onMounted(loadSale)
</script>

<style scoped>
.page {
  padding: 20px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.actions {
  display: flex;
  gap: 8px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 16px;
}
.table-wrap {
  overflow: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
}
.table th,
.table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px;
  text-align: left;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: white;
  color: #111827;
  text-decoration: none;
  cursor: pointer;
}
.btn-primary {
  background: #16a34a;
  color: #fff;
  border-color: #16a34a;
}
.btn-outline {
  background: transparent;
}
.payload {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  max-height: 300px;
  overflow: auto;
}
@media (max-width: 1024px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
