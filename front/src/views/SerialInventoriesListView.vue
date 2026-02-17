<template>
  <div class="page">
    <h2>Список инвентаризаций (QR)</h2>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Статус</label>
          <select v-model="filters.status" class="form-control">
            <option value="">Все</option>
            <option value="draft">draft</option>
            <option value="counting">counting</option>
            <option value="closed">closed</option>
            <option value="void">void</option>
          </select>
        </div>
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="filters.location_id" class="form-control">
            <option :value="0">Все</option>
            <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Лимит</label>
          <input v-model.number="filters.limit" type="number" min="1" max="500" class="form-control" />
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
              <th>Статус</th>
              <th>Локация</th>
              <th>Закрыт</th>
              <th>Создан</th>
              <th>Обновлен</th>
              <th>Автор</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.status }}</td>
              <td>{{ locationLabel(row.location_id) }}</td>
              <td>{{ formatDate(row.closed_at ?? null) }}</td>
              <td>{{ formatDate(row.created_at) }}</td>
              <td>{{ formatDate(row.updated_at) }}</td>
              <td>{{ row.created_by_user_id ?? '-' }}</td>
              <td>
                <RouterLink v-if="canView(row.status)" class="btn btn-outline" :to="`/serial/inventories/view/${row.id}`">
                  Просмотр
                </RouterLink>
                <RouterLink v-if="canEdit(row.status)" class="btn btn-outline" :to="`/serial/inventories/edit/${row.id}`">
                  Редактировать
                </RouterLink>
                <span v-if="!canView(row.status) && !canEdit(row.status)">-</span>
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
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type InventoryDocListOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const rows = ref<InventoryDocListOut[]>([])
const loading = ref(false)

const filters = ref({
  status: '',
  location_id: 0,
  limit: 100
})

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const canEdit = (status: string) => !['closed', 'void'].includes(status)
const canView = (status: string) => status === 'closed'

const loadRows = async () => {
  try {
    loading.value = true
    const params: Record<string, any> = { limit: filters.value.limit }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.location_id > 0) params.location_id = filters.value.location_id
    rows.value = await serialApi.listInventories(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = {
    status: '',
    location_id: 0,
    limit: 100
  }
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
