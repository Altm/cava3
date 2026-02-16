<template>
  <div class="page">
    <div class="page-head">
      <h2>Список коробок (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/boxes/manage">Создать коробку</RouterLink>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Статус</label>
          <select v-model="filters.status" class="form-control">
            <option value="">Все</option>
            <option value="active">active</option>
            <option value="voided">voided</option>
          </select>
        </div>
        <div class="form-group">
          <label>Состояние</label>
          <select v-model="filters.sealedRaw" class="form-control">
            <option value="">Все</option>
            <option value="true">sealed</option>
            <option value="false">open</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="filters.location_id" class="form-control">
            <option :value="0">Все</option>
            <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
          </select>
        </div>
        <div class="form-group">
          <label>Товар</label>
          <select v-model.number="filters.product_id" class="form-control">
            <option :value="0">Все</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Lot ID</label>
          <input v-model.number="filters.lot_id" type="number" min="0" class="form-control" />
        </div>
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
              <th>QR</th>
              <th>Статус</th>
              <th>Sealed</th>
              <th>Товар</th>
              <th>Lot</th>
              <th>Локация</th>
              <th>Создан</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.qr_code }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.sealed ? 'yes' : 'no' }}</td>
              <td>{{ productLabel(row.product_id) }}</td>
              <td>{{ row.lot_id }}</td>
              <td>{{ locationLabel(row.location_id) }}</td>
              <td>{{ formatDate(row.created_at) }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/serial/boxes/manage?box_id=${row.id}`">Редактировать</RouterLink>
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
import { productApi, type Location, type Product } from '@/api/productApi'
import { serialApi, type BoxListOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const rows = ref<BoxListOut[]>([])
const loading = ref(false)

const filters = ref({
  status: '',
  sealedRaw: '',
  location_id: 0,
  product_id: 0,
  lot_id: 0,
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

const productLabel = (productId: number) => {
  const product = products.value.find((p) => p.id === productId)
  return product ? `${product.name} (${productId})` : String(productId)
}

const loadRows = async () => {
  try {
    loading.value = true
    const params: Record<string, any> = { limit: filters.value.limit }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.sealedRaw === 'true') params.sealed = true
    if (filters.value.sealedRaw === 'false') params.sealed = false
    if (filters.value.location_id > 0) params.location_id = filters.value.location_id
    if (filters.value.product_id > 0) params.product_id = filters.value.product_id
    if (filters.value.lot_id > 0) params.lot_id = filters.value.lot_id
    rows.value = await serialApi.listBoxes(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = {
    status: '',
    sealedRaw: '',
    location_id: 0,
    product_id: 0,
    lot_id: 0,
    limit: 100
  }
  await loadRows()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
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
