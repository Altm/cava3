<template>
  <div class="page">
    <div class="page-head">
      <h2>Список продаж</h2>
      <RouterLink class="btn btn-outline" to="/sales">К созданию продажи</RouterLink>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Статус</label>
          <select v-model="filters.status" class="form-control">
            <option value="">Все</option>
            <option value="pending">pending</option>
            <option value="confirmed">confirmed</option>
          </select>
        </div>
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="filters.location_id" class="form-control">
            <option :value="0">Все</option>
            <option v-for="location in locations" :key="location.id" :value="location.id">
              {{ location.name }} ({{ location.code }})
            </option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Terminal ID</label>
          <input v-model.trim="filters.terminal_id" class="form-control" placeholder="Например T-1" />
        </div>
        <div class="form-group">
          <label>Лимит</label>
          <input v-model.number="filters.limit" type="number" min="1" max="500" class="form-control" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>С даты</label>
          <input v-model="filters.date_from" type="datetime-local" class="form-control" />
        </div>
        <div class="form-group">
          <label>По дату</label>
          <input v-model="filters.date_to" type="datetime-local" class="form-control" />
        </div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" @click="loadRows">Применить фильтры</button>
        <button class="btn btn-outline" @click="resetFilters">Сбросить</button>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Sale ID</th>
              <th>Статус</th>
              <th>Локация</th>
              <th>Terminal</th>
              <th>Пользователь</th>
              <th>Строк</th>
              <th>Сумма</th>
              <th>Создано</th>
              <th>Подтверждено</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.saleId ?? '-' }}</td>
              <td>{{ row.status }}</td>
              <td>{{ locationLabel(row.locationId, row.locationName) }}</td>
              <td>{{ row.terminalId || '-' }}</td>
              <td>{{ row.userId ?? '-' }}</td>
              <td>{{ row.linesCount }}</td>
              <td>{{ row.totalAmount }}</td>
              <td>{{ formatDate(row.createdAt) }}</td>
              <td>{{ formatDate(row.confirmedAt) }}</td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="10">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="10">Загрузка...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location, type SaleListItem } from '@/api/productApi'

const rows = ref<SaleListItem[]>([])
const locations = ref<Location[]>([])
const loading = ref(false)

const initialFilters = () => ({
  status: '',
  location_id: 0,
  terminal_id: '',
  date_from: '',
  date_to: '',
  limit: 100,
})

const filters = ref(initialFilters())

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const locationLabel = (locationId: number, fallbackName?: string | null) => {
  const location = locations.value.find((entry) => entry.id === locationId)
  if (location) return `${location.name} (${location.code})`
  if (fallbackName) return fallbackName
  return String(locationId)
}

const toIso = (value: string) => {
  if (!value) return undefined
  return `${value}:00`
}

const loadRows = async () => {
  try {
    loading.value = true
    rows.value = await productApi.getSalesList({
      status: filters.value.status || undefined,
      locationId: filters.value.location_id > 0 ? filters.value.location_id : undefined,
      terminalId: filters.value.terminal_id || undefined,
      dateFrom: toIso(filters.value.date_from),
      dateTo: toIso(filters.value.date_to),
      limit: filters.value.limit,
    })
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки списка продаж')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = initialFilters()
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
.form-group {
  margin-bottom: 12px;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
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
@media (max-width: 1024px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
