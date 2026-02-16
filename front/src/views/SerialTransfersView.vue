<template>
  <div class="page">
    <h2>Перемещение (QR)</h2>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Откуда (склад)</label>
            <select v-model.number="fromLocationId" class="form-control">
              <option :value="0">Выберите локацию</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
          <div class="form-group">
            <label>Куда (bar)</label>
            <select v-model.number="toLocationId" class="form-control">
              <option :value="0">Выберите локацию</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!canCreate" @click="createDoc">Создать</button>
          <button class="btn btn-outline" :disabled="!transferId" @click="ship">Отгрузить</button>
          <button class="btn btn-danger" :disabled="!transferId" @click="closeDoc">Закрыть (списать недостачу)</button>
        </div>
        <div v-if="transferId" class="meta">
          <div><b>ID:</b> {{ transferId }}</div>
          <div><b>Статус:</b> {{ transferStatus }}</div>
          <div><b>План:</b> {{ plannedTotal }} / <b>Pick:</b> {{ pickedTotal }} / <b>Получено:</b> {{ receivedTotal }}</div>
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
            <button class="btn btn-outline" :disabled="!transferId" @click="removePlannedByScan">Удалить из плана</button>
          </div>
        </div>

        <p class="hint">
          Подсказка: даже без списка planned можно идти по складу и сканировать любые ITM/BOX — система сама заменит
          позиции плана при необходимости.
        </p>
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
            <button class="btn btn-primary" :disabled="!transferId" @click="scanPicking">Скан</button>
          </div>
        </div>
        <pre v-if="pickLog.length" class="pre">{{ pickLog.join('\\n') }}</pre>
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
            <button class="btn btn-primary" :disabled="!transferId" @click="scanReceiving">Скан</button>
          </div>
        </div>
        <pre v-if="recvLog.length" class="pre">{{ recvLog.join('\\n') }}</pre>
      </div>
    </div>

    <div class="card">
      <h3>Просмотр созданных перемещений</h3>
      <div class="form-actions">
        <button class="btn btn-outline" @click="toggleTransfersList">
          {{ showTransfersList ? 'Скрыть список' : 'Показать список' }}
        </button>
        <button v-if="showTransfersList" class="btn btn-primary" @click="loadTransfersList">Обновить</button>
      </div>

      <div v-if="showTransfersList">
        <div class="form-row">
          <div class="form-group">
            <label>Статус</label>
            <select v-model="transferListFilters.status" class="form-control">
              <option value="">Все</option>
              <option value="draft">draft</option>
              <option value="picking">picking</option>
              <option value="shipped">shipped</option>
              <option value="closed">closed</option>
              <option value="canceled">canceled</option>
            </select>
          </div>
          <div class="form-group">
            <label>Откуда</label>
            <select v-model.number="transferListFilters.from_location_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Куда</label>
            <select v-model.number="transferListFilters.to_location_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
            </select>
          </div>
          <div class="form-group">
            <label>Товар</label>
            <select v-model.number="transferListFilters.product_id" class="form-control">
              <option :value="0">Все</option>
              <option v-for="p in serialProducts" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Лимит</label>
            <input v-model.number="transferListFilters.limit" type="number" min="1" max="500" class="form-control" />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" @click="loadTransfersList">Применить фильтры</button>
          <button class="btn btn-outline" @click="resetTransferListFilters">Сбросить</button>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Статус</th>
                <th>Откуда</th>
                <th>Куда</th>
                <th>Создан</th>
                <th>Обновлен</th>
                <th>Автор</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in transferRows" :key="row.id">
                <td>{{ row.id }}</td>
                <td>{{ row.status }}</td>
                <td>{{ locationLabel(row.from_location_id) }}</td>
                <td>{{ locationLabel(row.to_location_id) }}</td>
                <td>{{ formatDate(row.created_at) }}</td>
                <td>{{ formatDate(row.updated_at) }}</td>
                <td>{{ row.created_by_user_id ?? '-' }}</td>
              </tr>
              <tr v-if="!transferRows.length && !transferRowsLoading">
                <td colspan="7">Нет данных</td>
              </tr>
              <tr v-if="transferRowsLoading">
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
import { computed, onMounted, ref } from 'vue'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type TransferDocListOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])

const fromLocationId = ref(0)
const toLocationId = ref(0)
const transferId = ref<number | null>(null)
const transferStatus = ref('')

const plan = ref({ productId: 0, qtyBase: 1 })
const plannedTotal = ref(0)
const pickedTotal = ref(0)
const receivedTotal = ref(0)

const scanPickQr = ref('')
const scanRecvQr = ref('')
const removeItmQr = ref('')
const pickLog = ref<string[]>([])
const recvLog = ref<string[]>([])
const showTransfersList = ref(false)
const transferRowsLoading = ref(false)
const transferRows = ref<TransferDocListOut[]>([])
const transferListFilters = ref({
  status: '',
  from_location_id: 0,
  to_location_id: 0,
  product_id: 0,
  limit: 100
})

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => {
    const u = baseUnitsById.get(p.baseUnitId)
    return !!u?.isDiscrete
  })
})

const canCreate = computed(() => fromLocationId.value > 0 && toLocationId.value > 0 && fromLocationId.value !== toLocationId.value)
const canPlan = computed(() => !!transferId.value && plan.value.productId > 0 && plan.value.qtyBase > 0)

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const createDoc = async () => {
  try {
    const res = await serialApi.createTransfer(fromLocationId.value, toLocationId.value)
    transferId.value = res.id
    transferStatus.value = res.status
    plannedTotal.value = 0
    pickedTotal.value = 0
    receivedTotal.value = 0
    pickLog.value = []
    recvLog.value = []
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const planDoc = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.planTransfer(transferId.value, plan.value.productId, plan.value.qtyBase)
    plannedTotal.value += res.planned_items ?? res.plannedItems ?? plan.value.qtyBase
    transferStatus.value = 'picking'
    pickLog.value.unshift(`PLAN line_id=${res.transfer_line_id} planned=${res.planned_items}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const removePlannedByScan = async () => {
  if (!transferId.value) return
  try {
    const scan = await serialApi.scanQr(removeItmQr.value.trim())
    if (!scan.found || scan.kind !== 'ITM' || !scan.id) throw new Error('Не найден ITM')
    const res = await serialApi.removeTransferItem(transferId.value, scan.id)
    pickLog.value.unshift(`REMOVE product_item_id=${res.removed_product_item_id}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanPicking = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.scanTransfer(transferId.value, scanPickQr.value.trim(), 'picking')
    if (res.picked_item_id) pickedTotal.value += 1
    if (res.picked_items) pickedTotal.value += Number(res.picked_items)
    pickLog.value.unshift(`PICK ${scanPickQr.value.trim()} => ${JSON.stringify(res)}`)
    scanPickQr.value = ''
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const ship = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.shipTransfer(transferId.value)
    transferStatus.value = res.status ?? 'shipped'
    pickLog.value.unshift(`SHIP => ${JSON.stringify(res)}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanReceiving = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.scanTransfer(transferId.value, scanRecvQr.value.trim(), 'receiving')
    if (res.received_item_id) receivedTotal.value += 1
    if (res.received_items) receivedTotal.value += Number(res.received_items)
    recvLog.value.unshift(`RECV ${scanRecvQr.value.trim()} => ${JSON.stringify(res)}`)
    scanRecvQr.value = ''
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!transferId.value) return
  if (!confirm('Закрыть перемещение? Не принятое будет списано как lost_in_transit.')) return
  try {
    const res = await serialApi.closeTransfer(transferId.value)
    transferStatus.value = 'closed'
    recvLog.value.unshift(`CLOSE => ${JSON.stringify(res)}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const loadTransfersList = async () => {
  try {
    transferRowsLoading.value = true
    const params: Record<string, any> = { limit: transferListFilters.value.limit }
    if (transferListFilters.value.status) params.status = transferListFilters.value.status
    if (transferListFilters.value.from_location_id > 0) params.from_location_id = transferListFilters.value.from_location_id
    if (transferListFilters.value.to_location_id > 0) params.to_location_id = transferListFilters.value.to_location_id
    if (transferListFilters.value.product_id > 0) params.product_id = transferListFilters.value.product_id
    transferRows.value = await serialApi.listTransfers(params)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  } finally {
    transferRowsLoading.value = false
  }
}

const toggleTransfersList = async () => {
  showTransfersList.value = !showTransfersList.value
  if (showTransfersList.value) {
    await loadTransfersList()
  }
}

const resetTransferListFilters = async () => {
  transferListFilters.value = {
    status: '',
    from_location_id: 0,
    to_location_id: 0,
    product_id: 0,
    limit: 100
  }
  await loadTransfersList()
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
  units.value = await productApi.getUnits()
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
.meta {
  margin-top: 12px;
}
.pre {
  white-space: pre-wrap;
  background: #f7f7f7;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.hint {
  color: #4b5563;
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
