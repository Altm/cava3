<template>
  <div class="page">
    <h2>Сканер QR</h2>

    <form class="card" @submit.prevent="handleScan">
      <div class="form-group">
        <label>QR (ITM:... или BOX:...)</label>
        <input v-model="qr" placeholder="ITM:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" class="form-control" />
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit">Сканировать</button>
        <button class="btn btn-outline" type="button" @click="reset">Очистить</button>
      </div>
    </form>

    <div v-if="result" class="card">
      <h3>Результат</h3>
      <pre class="pre">{{ JSON.stringify(result, null, 2) }}</pre>
    </div>

    <div class="card">
      <h3>Списки</h3>
      <div class="form-actions">
        <button class="btn" :class="activeList === 'boxes' ? 'btn-primary' : 'btn-outline'" @click="toggleBoxesList">
          Коробки
        </button>
        <button class="btn" :class="activeList === 'items' ? 'btn-primary' : 'btn-outline'" @click="toggleItemsList">
          Единицы
        </button>
      </div>

      <div v-if="activeList === 'boxes'">
        <div class="form-row">
          <div class="form-group">
            <label>Статус</label>
            <select v-model="boxFilters.status" class="form-control">
              <option value="">Все</option>
              <option value="active">active</option>
              <option value="voided">voided</option>
            </select>
          </div>
          <div class="form-group">
            <label>Состояние</label>
            <select v-model="boxFilters.sealedRaw" class="form-control">
              <option value="">Все</option>
              <option value="true">sealed</option>
              <option value="false">open</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Локация</label>
            <select v-model.number="boxFilters.location_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
          <div class="form-group">
            <label>Товар</label>
            <select v-model.number="boxFilters.product_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Lot ID</label>
            <input v-model.number="boxFilters.lot_id" type="number" min="0" class="form-control" />
          </div>
          <div class="form-group">
            <label>Лимит</label>
            <input v-model.number="boxFilters.limit" type="number" min="1" max="500" class="form-control" />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="loadBoxes">Применить фильтры</button>
          <button class="btn btn-outline" @click="resetBoxFilters">Сбросить</button>
        </div>

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
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in boxesRows" :key="row.id">
                <td>{{ row.id }}</td>
                <td>{{ row.qr_code }}</td>
                <td>{{ row.status }}</td>
                <td>{{ row.sealed ? 'yes' : 'no' }}</td>
                <td>{{ productLabel(row.product_id) }}</td>
                <td>{{ row.lot_id }}</td>
                <td>{{ locationLabel(row.location_id) }}</td>
                <td>{{ formatDate(row.created_at) }}</td>
              </tr>
              <tr v-if="!boxesRows.length && !boxesLoading">
                <td colspan="8">Нет данных</td>
              </tr>
              <tr v-if="boxesLoading">
                <td colspan="8">Загрузка...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeList === 'items'">
        <div class="form-row">
          <div class="form-group">
            <label>Статус</label>
            <select v-model="itemFilters.status" class="form-control">
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
            <select v-model.number="itemFilters.location_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Товар</label>
            <select v-model.number="itemFilters.product_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
            </select>
          </div>
          <div class="form-group">
            <label>Lot ID</label>
            <input v-model.number="itemFilters.lot_id" type="number" min="0" class="form-control" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Box ID</label>
            <input v-model.number="itemFilters.box_id" type="number" min="0" class="form-control" />
          </div>
          <div class="form-group">
            <label>Reserved transfer_doc_id</label>
            <input v-model.number="itemFilters.reserved_transfer_doc_id" type="number" min="0" class="form-control" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Лимит</label>
            <input v-model.number="itemFilters.limit" type="number" min="1" max="500" class="form-control" />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="loadItems">Применить фильтры</button>
          <button class="btn btn-outline" @click="resetItemFilters">Сбросить</button>
        </div>

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
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in itemsRows" :key="row.id">
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
              </tr>
              <tr v-if="!itemsRows.length && !itemsLoading">
                <td colspan="10">Нет данных</td>
              </tr>
              <tr v-if="itemsLoading">
                <td colspan="10">Загрузка...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location, type Product } from '@/api/productApi'
import { serialApi, type BoxListOut, type ProductItemListOut } from '@/api/serialApi'

const qr = ref('')
const result = ref<any>(null)
const locations = ref<Location[]>([])
const products = ref<Product[]>([])

const activeList = ref<'boxes' | 'items' | null>(null)
const boxesLoading = ref(false)
const boxesRows = ref<BoxListOut[]>([])
const itemsLoading = ref(false)
const itemsRows = ref<ProductItemListOut[]>([])

const boxFilters = ref({
  status: '',
  sealedRaw: '',
  location_id: 0,
  product_id: 0,
  lot_id: 0,
  limit: 100
})

const itemFilters = ref({
  status: '',
  location_id: 0,
  product_id: 0,
  lot_id: 0,
  box_id: 0,
  reserved_transfer_doc_id: 0,
  limit: 100
})

const handleScan = async () => {
  try {
    result.value = await serialApi.scanQr(qr.value.trim())
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка сканирования')
  }
}

const reset = () => {
  qr.value = ''
  result.value = null
}

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const productLabel = (productId: number) => {
  const product = products.value.find((p) => p.id === productId)
  return product ? `${product.name} (${productId})` : String(productId)
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const loadBoxes = async () => {
  try {
    boxesLoading.value = true
    const params: Record<string, any> = { limit: boxFilters.value.limit }
    if (boxFilters.value.status) params.status = boxFilters.value.status
    if (boxFilters.value.sealedRaw === 'true') params.sealed = true
    if (boxFilters.value.sealedRaw === 'false') params.sealed = false
    if (boxFilters.value.location_id > 0) params.location_id = boxFilters.value.location_id
    if (boxFilters.value.product_id > 0) params.product_id = boxFilters.value.product_id
    if (boxFilters.value.lot_id > 0) params.lot_id = boxFilters.value.lot_id
    boxesRows.value = await serialApi.listBoxes(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    boxesLoading.value = false
  }
}

const loadItems = async () => {
  try {
    itemsLoading.value = true
    const params: Record<string, any> = { limit: itemFilters.value.limit }
    if (itemFilters.value.status) params.status = itemFilters.value.status
    if (itemFilters.value.location_id > 0) params.location_id = itemFilters.value.location_id
    if (itemFilters.value.product_id > 0) params.product_id = itemFilters.value.product_id
    if (itemFilters.value.lot_id > 0) params.lot_id = itemFilters.value.lot_id
    if (itemFilters.value.box_id > 0) params.box_id = itemFilters.value.box_id
    if (itemFilters.value.reserved_transfer_doc_id > 0) {
      params.reserved_transfer_doc_id = itemFilters.value.reserved_transfer_doc_id
    }
    itemsRows.value = await serialApi.listProductItems(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    itemsLoading.value = false
  }
}

const toggleBoxesList = async () => {
  if (activeList.value === 'boxes') {
    activeList.value = null
    return
  }
  activeList.value = 'boxes'
  await loadBoxes()
}

const toggleItemsList = async () => {
  if (activeList.value === 'items') {
    activeList.value = null
    return
  }
  activeList.value = 'items'
  await loadItems()
}

const resetBoxFilters = async () => {
  boxFilters.value = {
    status: '',
    sealedRaw: '',
    location_id: 0,
    product_id: 0,
    lot_id: 0,
    limit: 100
  }
  await loadBoxes()
}

const resetItemFilters = async () => {
  itemFilters.value = {
    status: '',
    location_id: 0,
    product_id: 0,
    lot_id: 0,
    box_id: 0,
    reserved_transfer_doc_id: 0,
    limit: 100
  }
  await loadItems()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
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
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: white;
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
.pre {
  white-space: pre-wrap;
  background: #f7f7f7;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.table-wrap {
  margin-top: 12px;
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
