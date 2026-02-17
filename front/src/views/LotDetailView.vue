<template>
  <div class="page">
    <div class="page-head">
      <h2>Партия #{{ lotId }}</h2>
      <RouterLink class="btn btn-outline" to="/lots">К списку партий</RouterLink>
    </div>

    <div v-if="detail" class="card">
      <div class="meta">
        <span><b>Товар:</b> {{ detail.productName }} (#{{ detail.productId }})</span>
        <span><b>Supplier Lot:</b> {{ detail.supplierLotNumber || '-' }}</span>
        <span><b>Закупка:</b> {{ detail.purchasePrice ?? '-' }}</span>
        <span><b>Дата партии:</b> {{ formatDate(detail.receivedAt) }}</span>
        <span><b>Приёмка:</b> #{{ detail.receiptId }} ({{ detail.receiptStatus }})</span>
        <span><b>Item всего:</b> {{ detail.totalItems }}</span>
        <span><b>Item в наличии:</b> {{ detail.inStockItems }}</span>
      </div>
    </div>

    <div class="card">
      <h3>Содержимое партии</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Item ID</th>
              <th>QR</th>
              <th>Статус</th>
              <th>Локация</th>
              <th>Коробка</th>
              <th>Создан</th>
              <th>Обновлён</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in detail?.items || []" :key="item.productItemId">
              <td>{{ item.productItemId }}</td>
              <td>{{ item.productItemQrCode }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.locationName }} (#{{ item.locationId }})</td>
              <td>{{ item.boxQrCode || '-' }}</td>
              <td>{{ formatDate(item.createdAt) }}</td>
              <td>{{ formatDate(item.updatedAt) }}</td>
            </tr>
            <tr v-if="detail && !detail.items.length">
              <td colspan="7">Партия пуста</td>
            </tr>
            <tr v-if="loading">
              <td colspan="7">Загрузка...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type LotDetail } from '@/api/productApi'

const route = useRoute()
const lotId = Number(route.params.id)
const detail = ref<LotDetail | null>(null)
const loading = ref(false)

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

onMounted(async () => {
  try {
    loading.value = true
    detail.value = await productApi.getLot(lotId)
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки партии')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page {
  padding: 20px;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
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
.btn-outline {
  background: transparent;
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
  font-size: 0.92rem;
}
</style>
