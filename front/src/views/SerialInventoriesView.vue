<template>
  <div class="page">
    <div class="page-head">
      <h2>Инвентаризация (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/inventories/list">Таблица инвентаризаций</RouterLink>
    </div>

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
            <button class="btn btn-primary" :disabled="!inventoryId || !scanQr.trim()" @click="scan">Скан</button>
          </div>
        </div>
        <pre v-if="log.length" class="pre">{{ log.join('\\n') }}</pre>
      </div>
    </div>

    <div v-if="inventoryId && expected" class="card">
      <h3>Предполагаемый список для сканирования</h3>
      <div class="meta"><b>Осталось к скану:</b> {{ expected.remaining_expected_count }}</div>

      <div class="table-wrap" v-if="expected.boxes.length">
        <table class="table">
          <thead>
            <tr>
              <th>Коробка</th>
              <th>QR</th>
              <th>Статус</th>
              <th>Осталось item</th>
              <th>Содержимое (для open)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="box in expected.boxes" :key="box.box_id" :class="box.sealed ? 'row-box-closed' : 'row-box-open'">
              <td>#{{ box.box_id }}</td>
              <td>{{ box.box_qr_code }}</td>
              <td>{{ box.sealed ? 'closed' : 'open' }}</td>
              <td>{{ box.items_remaining }}</td>
              <td>
                <div v-if="box.sealed">Сканируйте коробку целиком</div>
                <div v-else>
                  <div v-for="item in box.items" :key="item.product_item_id">
                    {{ item.product_item_id }} | {{ item.product_name }} | {{ item.product_item_qr_code }}
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="table-wrap" v-if="expected.single_items.length">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Название</th>
              <th>QR</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in expected.single_items" :key="item.product_item_id">
              <td>{{ item.product_item_id }}</td>
              <td>{{ item.product_name }}</td>
              <td>{{ item.product_item_qr_code }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!expected.boxes.length && !expected.single_items.length" class="meta">Нет элементов для сканирования</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type InventoryExpectedListOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const locationId = ref(0)

const inventoryId = ref<number | null>(null)
const status = ref('')
const expectedCount = ref(0)
const scannedCount = ref(0)

const scanQr = ref('')
const log = ref<string[]>([])
const expected = ref<InventoryExpectedListOut | null>(null)

const refreshDoc = async () => {
  if (!inventoryId.value) return
  const doc = await serialApi.getInventory(inventoryId.value)
  status.value = doc.status
  expectedCount.value = doc.expected_count
  scannedCount.value = doc.scanned_count
}

const loadExpected = async () => {
  if (!inventoryId.value) {
    expected.value = null
    return
  }
  expected.value = await serialApi.getInventoryExpected(inventoryId.value)
}

const createDoc = async () => {
  try {
    const res = await serialApi.createInventory(locationId.value)
    inventoryId.value = res.id
    status.value = res.status
    expectedCount.value = 0
    scannedCount.value = 0
    log.value = []
    await loadExpected()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const start = async () => {
  if (!inventoryId.value) return
  try {
    const res = await serialApi.startInventory(inventoryId.value)
    log.value.unshift(`START expected=${res.expected ?? 0}`)
    await refreshDoc()
    await loadExpected()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scan = async () => {
  if (!inventoryId.value) return
  try {
    const qr = scanQr.value.trim()
    if (!qr) return
    if (status.value === 'draft') {
      const startRes = await serialApi.startInventory(inventoryId.value)
      log.value.unshift(`AUTO-START expected=${startRes.expected ?? 0}`)
      await refreshDoc()
      await loadExpected()
    }
    if (status.value !== 'counting') {
      alert(`Документ в статусе "${status.value}". Сканирование недоступно.`)
      return
    }
    const res = await serialApi.scanInventory(inventoryId.value, scanQr.value.trim())
    log.value.unshift(`SCAN ${qr} => ${JSON.stringify(res)}`)
    scanQr.value = ''
    await refreshDoc()
    await loadExpected()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!inventoryId.value) return
  if (!confirm('Закрыть инвентаризацию? expected-not-scanned будет списано как lost (missing_inventory).')) return
  try {
    const res = await serialApi.closeInventory(inventoryId.value)
    log.value.unshift(`CLOSE missing=${res.missing ?? 0}`)
    await refreshDoc()
    await loadExpected()
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
  overflow: auto;
  margin-top: 12px;
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
.row-box-closed {
  background: #ecfdf5;
}
.row-box-open {
  background: #fef2f2;
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
