<template>
  <div class="page">
    <h2>Инвентаризация (QR)</h2>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="locationId" class="form-control">
            <option :value="0">Выберите локацию</option>
            <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
          </select>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!locationId" @click="createDoc">Создать</button>
          <button class="btn btn-outline" :disabled="!inventoryId" @click="start">Сформировать список</button>
          <button class="btn btn-danger" :disabled="!inventoryId" @click="closeDoc">Закрыть (списать missing)</button>
        </div>
        <div v-if="inventoryId" class="meta">
          <div><b>ID:</b> {{ inventoryId }}</div>
          <div><b>Статус:</b> {{ status }}</div>
          <div><b>Ожидается:</b> {{ expectedCount }} / <b>Скан:</b> {{ scannedCount }}</div>
        </div>
      </div>

      <div class="card">
        <h3>Сканирование</h3>
        <div class="form-row">
          <div class="form-group">
            <label>QR (ITM/BOX)</label>
            <input v-model="scanQr" class="form-control" placeholder="ITM:... или BOX:..." />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-primary" :disabled="!inventoryId" @click="scan">Скан</button>
          </div>
        </div>
        <pre v-if="log.length" class="pre">{{ log.join('\\n') }}</pre>
      </div>
    </div>

    <div class="card">
      <h3>Просмотр созданных инвентаризаций</h3>
      <div class="form-actions">
        <button class="btn btn-outline" @click="toggleInventoriesList">
          {{ showInventoriesList ? 'Скрыть список' : 'Показать список' }}
        </button>
        <button v-if="showInventoriesList" class="btn btn-primary" @click="loadInventoriesList">Обновить</button>
      </div>

      <div v-if="showInventoriesList">
        <div class="form-row">
          <div class="form-group">
            <label>Статус</label>
            <select v-model="inventoryListFilters.status" class="form-control">
              <option value="">Все</option>
              <option value="draft">draft</option>
              <option value="counting">counting</option>
              <option value="closed">closed</option>
              <option value="void">void</option>
            </select>
          </div>
          <div class="form-group">
            <label>Локация</label>
            <select v-model.number="inventoryListFilters.location_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Лимит</label>
            <input v-model.number="inventoryListFilters.limit" type="number" min="1" max="500" class="form-control" />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="loadInventoriesList">Применить фильтры</button>
          <button class="btn btn-outline" @click="resetInventoryListFilters">Сбросить</button>
        </div>

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
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in inventoryRows" :key="row.id">
                <td>{{ row.id }}</td>
                <td>{{ row.status }}</td>
                <td>{{ locationLabel(row.location_id) }}</td>
                <td>{{ formatDate(row.closed_at ?? null) }}</td>
                <td>{{ formatDate(row.created_at) }}</td>
                <td>{{ formatDate(row.updated_at) }}</td>
                <td>{{ row.created_by_user_id ?? '-' }}</td>
              </tr>
              <tr v-if="!inventoryRows.length && !inventoryRowsLoading">
                <td colspan="7">Нет данных</td>
              </tr>
              <tr v-if="inventoryRowsLoading">
                <td colspan="7">Загрузка...</td>
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
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type InventoryDocListOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const locationId = ref(0)

const inventoryId = ref<number | null>(null)
const status = ref('')
const expectedCount = ref(0)
const scannedCount = ref(0)

const scanQr = ref('')
const log = ref<string[]>([])
const showInventoriesList = ref(false)
const inventoryRowsLoading = ref(false)
const inventoryRows = ref<InventoryDocListOut[]>([])
const inventoryListFilters = ref({
  status: '',
  location_id: 0,
  limit: 100
})

const locationLabel = (locationValue: number) => {
  const location = locations.value.find((l) => l.id === locationValue)
  return location ? `${location.name} (${location.code})` : String(locationValue)
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const createDoc = async () => {
  try {
    const res = await serialApi.createInventory(locationId.value)
    inventoryId.value = res.id
    status.value = res.status
    expectedCount.value = 0
    scannedCount.value = 0
    log.value = []
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const start = async () => {
  if (!inventoryId.value) return
  try {
    const res = await serialApi.startInventory(inventoryId.value)
    status.value = 'counting'
    expectedCount.value = res.expected ?? 0
    log.value.unshift(`START expected=${expectedCount.value}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scan = async () => {
  if (!inventoryId.value) return
  try {
    const res = await serialApi.scanInventory(inventoryId.value, scanQr.value.trim())
    scannedCount.value += 1
    log.value.unshift(`SCAN ${scanQr.value.trim()} => ${JSON.stringify(res)}`)
    scanQr.value = ''
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!inventoryId.value) return
  if (!confirm('Закрыть инвентаризацию? expected-not-scanned будет списано как lost (missing_inventory).')) return
  try {
    const res = await serialApi.closeInventory(inventoryId.value)
    status.value = 'closed'
    log.value.unshift(`CLOSE missing=${res.missing ?? 0}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const loadInventoriesList = async () => {
  try {
    inventoryRowsLoading.value = true
    const params: Record<string, any> = { limit: inventoryListFilters.value.limit }
    if (inventoryListFilters.value.status) params.status = inventoryListFilters.value.status
    if (inventoryListFilters.value.location_id > 0) params.location_id = inventoryListFilters.value.location_id
    inventoryRows.value = await serialApi.listInventories(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    inventoryRowsLoading.value = false
  }
}

const toggleInventoriesList = async () => {
  showInventoriesList.value = !showInventoriesList.value
  if (showInventoriesList.value) {
    await loadInventoriesList()
  }
}

const resetInventoryListFilters = async () => {
  inventoryListFilters.value = {
    status: '',
    location_id: 0,
    limit: 100
  }
  await loadInventoriesList()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
})
</script>

<style scoped>
.page {
  padding: 20px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
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
.btn-danger {
  background: #dc2626;
  color: white;
  border-color: #dc2626;
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
  .grid {
    grid-template-columns: 1fr;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
