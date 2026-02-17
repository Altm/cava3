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
        <span>
          <b>Приёмка:</b>
          <RouterLink class="link" :to="`/serial/receipts/view/${detail.receiptId}`">#{{ detail.receiptId }}</RouterLink>
          ({{ detail.receiptStatus }})
        </span>
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
              <th>Текущая локация</th>
              <th>Коробка</th>
              <th>Создан</th>
              <th>Обновлён</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in detail?.items || []" :key="item.productItemId" :class="rowClass(item.boxId)">
              <td>
                <RouterLink class="link" :to="`/serial/items/history/${item.productItemId}`">#{{ item.productItemId }}</RouterLink>
              </td>
              <td>{{ item.productItemQrCode }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.locationName }} ({{ item.locationCode || '-' }})</td>
              <td>
                <RouterLink v-if="item.boxId" class="link" :to="`/serial/boxes/manage?box_id=${item.boxId}`">
                  {{ item.boxQrCode || `#${item.boxId}` }}
                </RouterLink>
                <span v-else>-</span>
              </td>
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
const boxRowPalette = ['box-tone-1', 'box-tone-2', 'box-tone-3', 'box-tone-4', 'box-tone-5', 'box-tone-6']

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const rowClass = (boxId?: number | null) => {
  if (!boxId) return 'item-no-box'
  return boxRowPalette[Math.abs(boxId) % boxRowPalette.length]
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
.link {
  color: #2563eb;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
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
.box-tone-1 td {
  background: #f8fafc;
}
.box-tone-2 td {
  background: #f0f9ff;
}
.box-tone-3 td {
  background: #f5f3ff;
}
.box-tone-4 td {
  background: #f0fdf4;
}
.box-tone-5 td {
  background: #fffbeb;
}
.box-tone-6 td {
  background: #fef2f2;
}
.item-no-box td {
  background: #ffffff;
}
</style>
