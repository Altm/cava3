<template>
  <div class="page">
    <div class="page-head">
      <h2>История item #{{ itemId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/scan/items">К списку единиц</RouterLink>
    </div>

    <div v-if="history" class="card">
      <h3>Сводка</h3>
      <div><b>QR:</b> {{ history.summary.product_item_qr_code }}</div>
      <div><b>Статус item:</b> {{ history.summary.product_item_status }}</div>
      <div><b>Локация:</b> {{ locationLabel(history.summary.product_item_location_id) }}</div>
      <div><b>Товар:</b> {{ history.summary.product_name }} (id={{ history.summary.product_id }})</div>
      <div><b>SKU:</b> {{ history.summary.product_sku ?? '-' }}</div>
      <div><b>Lot ID:</b> {{ history.summary.lot_id }}</div>
      <div><b>Текущая базовая стоимость:</b> {{ history.summary.current_base_cost }}</div>
      <div><b>Сумма покупки item:</b> {{ history.summary.item_purchase_amount }}</div>
    </div>

    <div v-if="history" class="card">
      <h3>Остатки по товару</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Локация</th>
              <th>Остаток</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in history.stock_balances" :key="row.location_id">
              <td>{{ row.location_name }} ({{ locationCode(row.location_id) }})</td>
              <td>{{ row.quantity }}</td>
            </tr>
            <tr v-if="!history.stock_balances.length">
              <td colspan="2">Нет остатков</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="history" class="card">
      <h3>История движения</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Тип</th>
              <th>Описание</th>
              <th>Документ</th>
              <th>Откуда</th>
              <th>Куда</th>
              <th>Статус</th>
              <th>Состояние item</th>
              <th>Дата события</th>
              <th>Дата отгрузки</th>
              <th>Дата приёмки</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in history.transfers" :key="`${row.event_type}-${row.transfer_created_at}-${row.doc_type}-${row.doc_id}-${index}`" :class="{ 'row-lost': row.is_lost }">
              <td>{{ movementTypeLabel(row.event_type) }}</td>
              <td>{{ row.event_description || '-' }}</td>
              <td>{{ docLabel(row.doc_type, row.doc_id, row.transfer_doc_id) }}</td>
              <td>{{ locationLabelOptional(row.from_location_id) }}</td>
              <td>{{ locationLabelOptional(row.to_location_id) }}</td>
              <td>{{ row.transfer_status || '-' }}</td>
              <td>{{ row.transfer_item_state || '-' }}</td>
              <td>{{ formatDate(row.transfer_created_at) }}</td>
              <td>{{ formatDate(row.shipped_at) }}</td>
              <td>{{ formatDate(row.received_at) }}</td>
            </tr>
            <tr v-if="!history.transfers.length">
              <td colspan="10">История движения отсутствует</td>
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
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type ProductItemHistoryOut } from '@/api/serialApi'

const route = useRoute()
const itemId = Number(route.params.id)
const history = ref<ProductItemHistoryOut | null>(null)
const locations = ref<Location[]>([])

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const location = (locationId: number) => locations.value.find((row) => row.id === locationId)
const locationLabel = (locationId: number) => {
  const row = location(locationId)
  return row ? `${row.name} (${row.code})` : String(locationId)
}
const locationCode = (locationId: number) => {
  const row = location(locationId)
  return row ? row.code : '-'
}

const locationLabelOptional = (locationId?: number | null) => {
  if (!locationId) return '-'
  return locationLabel(locationId)
}

const movementTypeLabel = (eventType: string) => {
  if (eventType === 'receipt') return 'Приёмка'
  if (eventType === 'sale') return 'Продажа'
  if (eventType === 'transfer') return 'Перемещение'
  return eventType
}

const docLabel = (docType?: string | null, docId?: number | null, transferDocId?: number | null) => {
  if (docType && docId) return `${docType} #${docId}`
  if (transferDocId) return `transfer #${transferDocId}`
  return '-'
}

onMounted(async () => {
  try {
    locations.value = await productApi.getLocations()
    history.value = await serialApi.getProductItemHistory(itemId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
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
  margin-bottom: 16px;
}
.page-head h2 {
  margin: 0;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
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
.row-lost {
  background: #fee2e2;
}
</style>
