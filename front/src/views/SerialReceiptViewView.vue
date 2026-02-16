<template>
  <div class="page">
    <div class="page-head">
      <h2>Содержимое приёмки #{{ receiptId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/receipts/list">К списку</RouterLink>
    </div>

    <div v-if="receipt" class="card">
      <div><b>Статус:</b> {{ receipt.status }}</div>
      <div><b>Локация:</b> {{ receipt.to_location_id }}</div>
      <div><b>Создан:</b> {{ formatDate(receipt.created_at) }}</div>
      <div><b>Обновлён:</b> {{ formatDate(receipt.updated_at) }}</div>
      <div><b>Всего item:</b> {{ rows.length }}</div>
      <div><b>Сумма покупки (item):</b> {{ totalPurchaseAmount.toFixed(2) }}</div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Item ID</th>
              <th>QR</th>
              <th>Товар</th>
              <th>Стоимость покупки</th>
              <th>Партия</th>
              <th>Дата партии</th>
              <th>Статус item</th>
              <th>Локация</th>
              <th>Коробка</th>
              <th>Создан item</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.product_item_id">
              <td>{{ row.product_item_id }}</td>
              <td>{{ row.product_item_qr_code }}</td>
              <td>{{ row.product_name }} ({{ row.product_sku ?? '-' }})</td>
              <td>{{ row.purchase_amount }}</td>
              <td>{{ row.lot_id }} / {{ row.supplier_lot_number ?? '-' }}</td>
              <td>{{ formatDate(row.lot_received_at) }}</td>
              <td>{{ row.product_item_status }}</td>
              <td>{{ row.location_name }} ({{ row.location_code }})</td>
              <td>{{ row.box_qr_code ?? '-' }}</td>
              <td>{{ formatDate(row.product_item_created_at) }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/serial/items/history/${row.product_item_id}`">История</RouterLink>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="11">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="11">Загрузка...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { serialApi, type ReceiptDetailOut, type ReceiptItemContentOut } from '@/api/serialApi'

const route = useRoute()
const receiptId = Number(route.params.id)
const receipt = ref<ReceiptDetailOut | null>(null)
const rows = ref<ReceiptItemContentOut[]>([])
const loading = ref(false)

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const totalPurchaseAmount = computed(() =>
  rows.value.reduce((acc, row) => acc + Number(row.purchase_amount || 0), 0)
)

const load = async () => {
  try {
    loading.value = true
    receipt.value = await serialApi.getReceipt(receiptId)
    rows.value = await serialApi.listReceiptItems(receiptId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    loading.value = false
  }
}

onMounted(load)
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
</style>
