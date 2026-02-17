<template>
  <div class="page">
    <div class="page-head">
      <h2>Редактирование инвентаризации #{{ inventoryId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/inventories/list">К списку</RouterLink>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>
        <div class="meta" v-if="doc">
          <div><b>Статус:</b> {{ doc.status }}</div>
          <div><b>Локация:</b> {{ locationLabel(doc.location_id) }}</div>
          <div>
            <b>Expected:</b> {{ doc.expected_count }} /
            <b>Scanned:</b> {{ doc.scanned_count }} /
            <b>Missing:</b> {{ doc.missing_count }} /
            <b>Unexpected:</b> {{ doc.unexpected_count }}
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-outline" :disabled="!canStart" @click="start">Сформировать список</button>
          <button class="btn btn-danger" :disabled="!canClose" @click="closeDoc">Закрыть (списать missing)</button>
          <button class="btn btn-primary" @click="reload">Обновить</button>
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
            <button class="btn btn-primary" :disabled="!canScan" @click="scan">Скан</button>
          </div>
        </div>
        <pre v-if="log.length" class="pre">{{ log.join('\n') }}</pre>
      </div>
    </div>

    <div v-if="expected" class="card">
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
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type InventoryDocDetailOut, type InventoryExpectedListOut } from '@/api/serialApi'

const route = useRoute()
const inventoryId = Number(route.params.id)

const locations = ref<Location[]>([])
const doc = ref<InventoryDocDetailOut | null>(null)
const expected = ref<InventoryExpectedListOut | null>(null)
const scanQr = ref('')
const log = ref<string[]>([])

const canStart = computed(() => doc.value?.status === 'draft')
const canScan = computed(() => doc.value?.status === 'counting' || doc.value?.status === 'draft')
const canClose = computed(() => doc.value?.status === 'counting')

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const reload = async () => {
  try {
    doc.value = await serialApi.getInventory(inventoryId)
    expected.value = await serialApi.getInventoryExpected(inventoryId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const start = async () => {
  try {
    const res = await serialApi.startInventory(inventoryId)
    log.value.unshift(`START => ${JSON.stringify(res)}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scan = async () => {
  try {
    const qr = scanQr.value.trim()
    if (!qr) return
    if (doc.value?.status === 'draft') {
      const startRes = await serialApi.startInventory(inventoryId)
      log.value.unshift(`AUTO-START => ${JSON.stringify(startRes)}`)
      await reload()
    }
    if (doc.value?.status !== 'counting') {
      alert(`Документ в статусе "${doc.value?.status ?? '-'}". Сканирование недоступно.`)
      return
    }
    const res = await serialApi.scanInventory(inventoryId, qr)
    log.value.unshift(`SCAN ${qr} => ${JSON.stringify(res)}`)
    scanQr.value = ''
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!confirm('Закрыть инвентаризацию? expected-not-scanned будет списано как lost.')) return
  try {
    const res = await serialApi.closeInventory(inventoryId)
    log.value.unshift(`CLOSE => ${JSON.stringify(res)}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  await reload()
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
.meta {
  margin-bottom: 12px;
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
