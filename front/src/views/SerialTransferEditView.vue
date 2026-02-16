<template>
  <div class="page">
    <div class="page-head">
      <h2>Редактирование перемещения #{{ transferId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/transfers/list">К списку</RouterLink>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>
        <div v-if="doc" class="meta">
          <div><b>Статус:</b> {{ doc.status }}</div>
          <div><b>Откуда:</b> {{ locationLabel(doc.from_location_id) }}</div>
          <div><b>Куда:</b> {{ locationLabel(doc.to_location_id) }}</div>
          <div>
            <b>Planned:</b> {{ doc.planned_count }} /
            <b>Picked:</b> {{ doc.picked_count }} /
            <b>Received:</b> {{ doc.received_count }} /
            <b>Removed:</b> {{ doc.removed_count }}
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-outline" :disabled="!canShip" @click="ship">Отгрузить</button>
          <button class="btn btn-danger" :disabled="!canClose" @click="closeDoc">Закрыть (списать недостачу)</button>
          <button class="btn btn-primary" @click="reload">Обновить</button>
        </div>
      </div>

      <div class="card">
        <h3>Планирование (FIFO)</h3>
        <div class="form-group">
          <label>Товар</label>
          <select v-model.number="plan.productId" class="form-control">
            <option :value="0">Выберите товар</option>
            <option v-for="p in serialProducts" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Количество (шт, base)</label>
            <input v-model.number="plan.qtyBase" type="number" min="1" step="1" class="form-control" />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-primary" :disabled="!canPlan" @click="planDoc">Сформировать план</button>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Удалить planned item: скан ITM</label>
            <input v-model="removeItmQr" class="form-control" placeholder="ITM:..." />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-outline" :disabled="!canEditTransfer" @click="removePlannedByScan">Удалить из плана</button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Сканирование на складе (picking)</h3>
        <div class="form-row">
          <div class="form-group">
            <label>QR (ITM/BOX)</label>
            <input v-model="scanPickQr" class="form-control" placeholder="ITM:... или BOX:..." />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-primary" :disabled="!canScanPicking" @click="scanPicking">Скан</button>
          </div>
        </div>
        <pre v-if="pickLog.length" class="pre">{{ pickLog.join('\n') }}</pre>
      </div>

      <div class="card">
        <h3>Сканирование в баре (receiving)</h3>
        <div class="form-row">
          <div class="form-group">
            <label>QR (ITM/BOX)</label>
            <input v-model="scanRecvQr" class="form-control" placeholder="ITM:... или BOX:..." />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-primary" :disabled="!canScanReceiving" @click="scanReceiving">Скан</button>
          </div>
        </div>
        <pre v-if="recvLog.length" class="pre">{{ recvLog.join('\n') }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type TransferDocDetailOut } from '@/api/serialApi'

const route = useRoute()
const transferId = Number(route.params.id)

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const doc = ref<TransferDocDetailOut | null>(null)

const plan = ref({ productId: 0, qtyBase: 1 })
const scanPickQr = ref('')
const scanRecvQr = ref('')
const removeItmQr = ref('')
const pickLog = ref<string[]>([])
const recvLog = ref<string[]>([])

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => !!baseUnitsById.get(p.baseUnitId)?.isDiscrete)
})

const canEditTransfer = computed(() => doc.value != null && ['draft', 'picking', 'shipped'].includes(doc.value.status))
const canPlan = computed(() => doc.value != null && ['draft', 'picking'].includes(doc.value.status) && plan.value.productId > 0 && plan.value.qtyBase > 0)
const canScanPicking = computed(() => doc.value?.status === 'picking')
const canScanReceiving = computed(() => doc.value?.status === 'shipped')
const canShip = computed(() => doc.value?.status === 'picking')
const canClose = computed(() => doc.value?.status === 'shipped')

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const reload = async () => {
  try {
    doc.value = await serialApi.getTransfer(transferId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const planDoc = async () => {
  try {
    const res = await serialApi.planTransfer(transferId, plan.value.productId, plan.value.qtyBase)
    pickLog.value.unshift(`PLAN line_id=${res.transfer_line_id} planned=${res.planned_items}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const removePlannedByScan = async () => {
  try {
    const scan = await serialApi.scanQr(removeItmQr.value.trim())
    if (!scan.found || scan.kind !== 'ITM' || !scan.id) throw new Error('Не найден ITM')
    const res = await serialApi.removeTransferItem(transferId, scan.id)
    pickLog.value.unshift(`REMOVE product_item_id=${res.removed_product_item_id}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanPicking = async () => {
  try {
    const res = await serialApi.scanTransfer(transferId, scanPickQr.value.trim(), 'picking')
    pickLog.value.unshift(`PICK ${scanPickQr.value.trim()} => ${JSON.stringify(res)}`)
    scanPickQr.value = ''
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanReceiving = async () => {
  try {
    const res = await serialApi.scanTransfer(transferId, scanRecvQr.value.trim(), 'receiving')
    recvLog.value.unshift(`RECV ${scanRecvQr.value.trim()} => ${JSON.stringify(res)}`)
    scanRecvQr.value = ''
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const ship = async () => {
  try {
    const res = await serialApi.shipTransfer(transferId)
    pickLog.value.unshift(`SHIP => ${JSON.stringify(res)}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!confirm('Закрыть перемещение? Не принятое будет списано как lost_in_transit.')) return
  try {
    const res = await serialApi.closeTransfer(transferId)
    recvLog.value.unshift(`CLOSE => ${JSON.stringify(res)}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
  units.value = await productApi.getUnits()
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
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
