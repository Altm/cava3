<template>
  <div class="page">
    <div class="page-head">
      <h2>Общий лог единиц (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/scan/items">К списку единиц</RouterLink>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Товар</label>
          <input
            v-model="productQuery"
            list="item-log-products"
            class="form-control"
            placeholder="Все товары"
            @input="syncProductFilterByQuery"
          />
          <small v-if="filters.product_id > 0" class="hint">Выбран product_id={{ filters.product_id }}</small>
        </div>
        <div class="form-group">
          <label>Item ID</label>
          <input v-model.number="filters.product_item_id" type="number" min="0" class="form-control" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="filters.location_id" class="form-control">
            <option :value="0">Все</option>
            <option v-for="location in locations" :key="location.id" :value="location.id">
              {{ location.name }} ({{ location.code }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Тип события</label>
          <select v-model="filters.event_type" class="form-control">
            <option value="">Все</option>
            <option value="receipt">receipt</option>
            <option value="transfer_planned">transfer_planned</option>
            <option value="transfer_picked">transfer_picked</option>
            <option value="transfer_received">transfer_received</option>
            <option value="transfer_removed">transfer_removed</option>
            <option value="status_sold">status_sold</option>
            <option value="status_lost">status_lost</option>
            <option value="status_damaged">status_damaged</option>
            <option value="status_voided">status_voided</option>
          </select>
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
              <th>Дата</th>
              <th>Событие</th>
              <th>Item ID</th>
              <th>QR</th>
              <th>Товар</th>
              <th>Локация</th>
              <th>Откуда → Куда</th>
              <th>Документ</th>
              <th>Детали</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="`${row.event_time}-${row.event_type}-${row.product_item_id}-${row.doc_type}-${row.doc_id}`">
              <td>{{ formatDate(row.event_time) }}</td>
              <td>{{ row.event_type }}</td>
              <td>{{ row.product_item_id }}</td>
              <td>{{ row.product_item_qr_code }}</td>
              <td>{{ row.product_name }} ({{ row.product_id }})</td>
              <td>{{ locationLabel(row.location_id) }}</td>
              <td>{{ moveLabel(row.from_location_id, row.to_location_id) }}</td>
              <td>{{ docLabel(row.doc_type, row.doc_id) }}</td>
              <td>{{ row.details ?? '-' }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/serial/items/history/${row.product_item_id}`">История</RouterLink>
              </td>
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

    <datalist id="item-log-products">
      <option
        v-for="product in productAutocomplete.productOptions.value"
        :key="product.id"
        :value="productAutocomplete.formatProductOption(product)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { productApi, type Location, type Product } from '@/api/productApi'
import { serialApi, type ProductItemLogOut } from '@/api/serialApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'

const rows = ref<ProductItemLogOut[]>([])
const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const loading = ref(false)
const productQuery = ref('')

const filters = ref({
  product_item_id: 0,
  product_id: 0,
  location_id: 0,
  event_type: '',
  date_from: '',
  date_to: '',
  limit: 100,
})

const productAutocomplete = useProductAutocomplete(products, productQuery)

const syncProductFilterByQuery = () => {
  filters.value.product_id = productAutocomplete.parseProductIdFromQuery(productQuery.value)
}

const toIso = (value: string) => {
  if (!value) return undefined
  return `${value}:00`
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const locationLabel = (locationId?: number | null) => {
  if (!locationId) return '-'
  const location = locations.value.find((row) => row.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const moveLabel = (fromLocationId?: number | null, toLocationId?: number | null) => {
  if (!fromLocationId && !toLocationId) return '-'
  return `${locationLabel(fromLocationId)} → ${locationLabel(toLocationId)}`
}

const docLabel = (docType?: string | null, docId?: number | null) => {
  if (!docType && !docId) return '-'
  if (!docId) return String(docType)
  return `${docType ?? 'doc'} #${docId}`
}

const loadRows = async () => {
  try {
    loading.value = true
    const params: Record<string, any> = { limit: filters.value.limit }
    if (filters.value.product_item_id > 0) params.product_item_id = filters.value.product_item_id
    if (filters.value.product_id > 0) params.product_id = filters.value.product_id
    if (filters.value.location_id > 0) params.location_id = filters.value.location_id
    if (filters.value.event_type) params.event_type = filters.value.event_type
    if (filters.value.date_from) params.date_from = toIso(filters.value.date_from)
    if (filters.value.date_to) params.date_to = toIso(filters.value.date_to)
    rows.value = await serialApi.listProductItemLog(params)
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.value = {
    product_item_id: 0,
    product_id: 0,
    location_id: 0,
    event_type: '',
    date_from: '',
    date_to: '',
    limit: 100,
  }
  await loadRows()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
  await loadRows()
})

watch(
  () => filters.value.product_id,
  (productId) => {
    productAutocomplete.syncQueryBySelectedProductId(productId)
  }
)
</script>

<style scoped>
.page {
  padding: 20px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
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
