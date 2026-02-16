<template>
  <div class="page">
    <div class="page-head">
      <h2>Просмотр перемещения #{{ transferId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/transfers/list">К списку</RouterLink>
    </div>

    <div v-if="doc" class="card">
      <div><b>Статус:</b> {{ doc.status }}</div>
      <div><b>Откуда:</b> {{ locationLabel(doc.from_location_id) }}</div>
      <div><b>Куда:</b> {{ locationLabel(doc.to_location_id) }}</div>
      <div><b>Создан:</b> {{ formatDate(doc.created_at) }}</div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Item ID</th>
              <th>QR</th>
              <th>Товар</th>
              <th>Статус перемещения</th>
              <th>Состояние item</th>
              <th>Дата создания</th>
              <th>Дата отгрузки</th>
              <th>Дата приёмки</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.transfer_item_id" :class="{ 'row-lost': row.is_lost }">
              <td>{{ row.product_item_id }}</td>
              <td>{{ row.product_item_qr_code }}</td>
              <td>{{ row.product_name }} (id={{ row.product_id }})</td>
              <td>{{ row.transfer_status }}</td>
              <td>{{ row.transfer_item_state }}</td>
              <td>{{ formatDate(row.transfer_created_at) }}</td>
              <td>{{ formatDate(row.shipped_at) }}</td>
              <td>{{ formatDate(row.received_at) }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/serial/items/history/${row.product_item_id}`">История item</RouterLink>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="9">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="9">Загрузка...</td>
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
import { serialApi, type TransferDocDetailOut, type TransferItemMovementOut } from '@/api/serialApi'

const route = useRoute()
const transferId = Number(route.params.id)
const locations = ref<Location[]>([])
const doc = ref<TransferDocDetailOut | null>(null)
const rows = ref<TransferItemMovementOut[]>([])
const loading = ref(false)

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const load = async () => {
  try {
    loading.value = true
    doc.value = await serialApi.getTransfer(transferId)
    rows.value = await serialApi.listTransferItems(transferId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  await load()
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
