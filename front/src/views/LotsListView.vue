<template>
  <div class="page">
    <div class="page-head">
      <h2>Список партий</h2>
      <RouterLink class="btn btn-outline" to="/prices">К прайсам</RouterLink>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="filters.locationId" class="form-control">
            <option :value="0">Все</option>
            <option v-for="location in locations" :key="location.id" :value="location.id">
              {{ location.name }} ({{ location.code }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Товар</label>
          <input v-model.number="filters.productId" type="number" class="form-control" placeholder="ID товара" />
        </div>
        <div class="form-group">
          <label>Lot ID</label>
          <input v-model.number="filters.lotId" type="number" class="form-control" placeholder="ID партии" />
        </div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" @click="loadRows">Применить</button>
        <button class="btn btn-outline" @click="resetFilters">Сбросить</button>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Lot ID</th>
              <th>Товар</th>
              <th>Supplier Lot</th>
              <th>Дата партии</th>
              <th>Закупка</th>
              <th>Локация</th>
              <th>В наличии (item)</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.lotId">
              <td>{{ row.lotId }}</td>
              <td>{{ row.productName }} (#{{ row.productId }})</td>
              <td>{{ row.supplierLotNumber || '-' }}</td>
              <td>{{ formatDate(row.receivedAt) }}</td>
              <td>{{ row.purchasePrice ?? '-' }}</td>
              <td>{{ row.locationName }} ({{ row.locationCode }})</td>
              <td>{{ row.inStockItems }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/lots/${row.lotId}`">Просмотр</RouterLink>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="8">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="8">Загрузка...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location, type LotListItem } from '@/api/productApi'

const locations = ref<Location[]>([])
const rows = ref<LotListItem[]>([])
const loading = ref(false)

const filters = ref({
  locationId: 0,
  productId: 0,
  lotId: 0,
})

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const loadRows = async () => {
  try {
    loading.value = true
    rows.value = await productApi.listLots({
      locationId: filters.value.locationId > 0 ? filters.value.locationId : undefined,
      productId: filters.value.productId > 0 ? filters.value.productId : undefined,
      lotId: filters.value.lotId > 0 ? filters.value.lotId : undefined,
      limit: 500,
    })
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки партий')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = { locationId: 0, productId: 0, lotId: 0 }
  await loadRows()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  await loadRows()
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
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
.form-group {
  margin-bottom: 12px;
}
.form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.form-actions {
  display: flex;
  gap: 8px;
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
  background: #2563eb;
  color: white;
  border-color: #2563eb;
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
@media (max-width: 1200px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
