<template>
  <div class="page">
    <h2>Список единиц (QR)</h2>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Статус</label>
          <select v-model="filters.status" class="form-control">
            <option value="">Все</option>
            <option value="receiving">receiving</option>
            <option value="in_stock">in_stock</option>
            <option value="in_transit">in_transit</option>
            <option value="sold">sold</option>
            <option value="damaged">damaged</option>
            <option value="lost">lost</option>
            <option value="voided">voided</option>
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
          <label>Товар</label>
          <input
            v-model="productQuery"
            list="items-list-products"
            class="form-control"
            placeholder="Все товары"
            @input="syncProductFilterByQuery"
          />
          <small v-if="filters.product_id > 0" class="hint">Выбран product_id={{ filters.product_id }}</small>
        </div>
        <div class="form-group">
          <label>Lot ID</label>
          <input v-model.number="filters.lot_id" type="number" min="0" class="form-control" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Box ID</label>
          <input v-model.number="filters.box_id" type="number" min="0" class="form-control" />
        </div>
        <div class="form-group">
          <label>Reserved transfer_doc_id</label>
          <input v-model.number="filters.reserved_transfer_doc_id" type="number" min="0" class="form-control" />
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
              <th>QR</th>
              <th>Статус</th>
              <th>Товар</th>
              <th>Lot</th>
              <th>Локация</th>
              <th>Box</th>
              <th>Reserved</th>
              <th>Loss reason</th>
              <th>Создан</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.qr_code }}</td>
              <td>{{ row.status }}</td>
              <td>{{ productLabel(row.product_id) }}</td>
              <td>{{ row.lot_id }}</td>
              <td>{{ locationLabel(row.location_id) }}</td>
              <td>{{ row.box_id ?? '-' }}</td>
              <td>{{ row.reserved_transfer_doc_id ?? '-' }}</td>
              <td>{{ row.lost_reason ?? '-' }}</td>
              <td>{{ formatDate(row.created_at) }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/serial/items/history/${row.id}`">История</RouterLink>
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

    <datalist id="items-list-products">
      <option
        v-for="p in productAutocomplete.productOptions.value"
        :key="p.id"
        :value="productAutocomplete.formatProductOption(p)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { productApi, type Location, type Product } from '@/api/productApi'
import { serialApi, type ProductItemListOut } from '@/api/serialApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const rows = ref<ProductItemListOut[]>([])
const loading = ref(false)
const productQuery = ref('')

const filters = ref({
  status: '',
  location_id: 0,
  product_id: 0,
  lot_id: 0,
  box_id: 0,
  reserved_transfer_doc_id: 0,
  limit: 100
})
const productAutocomplete = useProductAutocomplete(products, productQuery)

const syncProductFilterByQuery = () => {
  filters.value.product_id = productAutocomplete.parseProductIdFromQuery(productQuery.value)
}

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
    if (filters.value.location_id > 0) params.location_id = filters.value.location_id
    if (filters.value.product_id > 0) params.product_id = filters.value.product_id
    if (filters.value.lot_id > 0) params.lot_id = filters.value.lot_id
    if (filters.value.box_id > 0) params.box_id = filters.value.box_id
    if (filters.value.reserved_transfer_doc_id > 0) {
      params.reserved_transfer_doc_id = filters.value.reserved_transfer_doc_id
    }
    rows.value = await serialApi.listProductItems(params)
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
    product_id: 0,
    lot_id: 0,
    box_id: 0,
    reserved_transfer_doc_id: 0,
    limit: 100
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
