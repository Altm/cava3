<template>
  <div class="page">
    <div class="page-head">
      <h2>Список прайсов</h2>
      <RouterLink class="btn btn-outline" to="/prices">К управлению</RouterLink>
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
          <label>Дата начала (>=)</label>
          <input v-model="filters.dateFrom" type="datetime-local" class="form-control" />
        </div>
        <div class="form-group">
          <label>Дата конца (<=)</label>
          <input v-model="filters.dateTo" type="datetime-local" class="form-control" />
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
              <th>ID</th>
              <th>Локация</th>
              <th>Режим</th>
              <th>Расчёт</th>
              <th>Название</th>
              <th>Начало</th>
              <th>Конец</th>
              <th>Строк</th>
              <th>Автор</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.locationName || row.locationId }}</td>
              <td>{{ row.mode }}</td>
              <td>{{ row.calculatorName ? `${row.calculatorName} v${row.calculatorVersion || '-'}` : '-' }}</td>
              <td>{{ row.name || '-' }}</td>
              <td>{{ formatDate(row.effectiveFrom) }}</td>
              <td>{{ row.effectiveTo ? formatDate(row.effectiveTo) : 'по настоящее время' }}</td>
              <td>{{ row.itemsCount }}</td>
              <td>{{ row.createdByUserId ?? '-' }}</td>
              <td><button class="btn btn-outline" @click="loadDetail(row.id)">Просмотр</button></td>
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

    <div v-if="detail" class="card">
      <h3>Ревизия #{{ detail.id }} — {{ detail.name || detail.mode }}</h3>
      <div class="meta">
        <span><b>Локация:</b> {{ detail.locationName || detail.locationId }}</span>
        <span><b>Дата:</b> {{ formatDate(detail.createdAt) }}</span>
        <span><b>Режим:</b> {{ detail.mode }}</span>
        <span><b>Расчёт:</b> {{ detail.calculatorName ? `${detail.calculatorName} v${detail.calculatorVersion || '-'}` : '-' }}</span>
        <span><b>Hash:</b> {{ detail.calculatorSourceHash || '-' }}</span>
        <span><b>Автор:</b> {{ detail.createdByUserId ?? '-' }}</span>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Товар</th>
              <th>Unit</th>
              <th>Было</th>
              <th>Стало</th>
              <th>Валюта</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in detail.items" :key="`item-${item.productId}-${item.unitId}`">
              <td>{{ item.productName }}</td>
              <td>{{ item.unitCode }}</td>
              <td>{{ item.previousAmount ?? '-' }}</td>
              <td>{{ item.amount }}</td>
              <td>{{ item.currency }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location, type PriceRevisionDetail, type PriceRevisionListItem } from '@/api/productApi'

const locations = ref<Location[]>([])
const rows = ref<PriceRevisionListItem[]>([])
const detail = ref<PriceRevisionDetail | null>(null)
const loading = ref(false)

const filters = ref({
  locationId: 0,
  dateFrom: '',
  dateTo: '',
})

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const toIso = (value: string) => {
  if (!value) return undefined
  return `${value}:00`
}

const loadRows = async () => {
  try {
    loading.value = true
    rows.value = await productApi.listPriceRevisions({
      locationId: filters.value.locationId > 0 ? filters.value.locationId : undefined,
      dateFrom: toIso(filters.value.dateFrom),
      dateTo: toIso(filters.value.dateTo),
      limit: 500,
    })
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки прайсов')
  } finally {
    loading.value = false
  }
}

const loadDetail = async (revisionId: number) => {
  try {
    detail.value = await productApi.getPriceRevision(revisionId)
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки ревизии')
  }
}

const resetFilters = async () => {
  filters.value = { locationId: 0, dateFrom: '', dateTo: '' }
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
  flex-wrap: wrap;
}
.meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
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
