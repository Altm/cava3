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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location } from '@/api/productApi'
import { serialApi } from '@/api/serialApi'

const locations = ref<Location[]>([])
const locationId = ref(0)

const inventoryId = ref<number | null>(null)
const status = ref('')
const expectedCount = ref(0)
const scannedCount = ref(0)

const scanQr = ref('')
const log = ref<string[]>([])

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
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>

