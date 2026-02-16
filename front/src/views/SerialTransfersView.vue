<template>
  <div class="page">
    <div class="page-head">
      <h2>Перемещение (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/transfers/list">Таблица перемещений</RouterLink>
    </div>

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

    <div v-if="transferId" class="card">
      <h3>План перемещения</h3>
      <div v-if="transferLines.length" class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Товар</th>
              <th>Политика</th>
              <th>План (шт)</th>
              <th>Планируемые QR (ITM)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in transferLines" :key="line.transfer_line_id">
              <td>{{ line.product_name }} (id={{ line.product_id }})</td>
              <td>{{ line.pick_policy }}</td>
              <td>{{ line.qty_base }}</td>
              <td>
                <div v-if="line.planned_qr_codes.length" class="qr-list">
                  <code v-for="qr in line.planned_qr_codes" :key="`${line.transfer_line_id}-${qr}`">{{ qr }}</code>
                </div>
                <span v-else>-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">План пока пуст.</p>
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

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type TransferDocDetailOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])

const fromLocationId = ref(0)
const toLocationId = ref(0)
const transferId = ref<number | null>(null)
const transferStatus = ref('')
const transferDetail = ref<TransferDocDetailOut | null>(null)

const plan = ref({ productId: 0, qtyBase: 1 })
const plannedTotal = ref(0)
const pickedTotal = ref(0)
const receivedTotal = ref(0)
const transferLines = computed(() => transferDetail.value?.transfer_lines ?? [])

const scanPickQr = ref('')
const scanRecvQr = ref('')
const removeItmQr = ref('')
const pickLog = ref<string[]>([])
const recvLog = ref<string[]>([])

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => {
    const u = baseUnitsById.get(p.baseUnitId)
    return !!u?.isDiscrete
  })
})

const canCreate = computed(() => fromLocationId.value > 0 && toLocationId.value > 0 && fromLocationId.value !== toLocationId.value)
const canPlan = computed(
  () =>
    !!transferId.value &&
    ['draft', 'picking'].includes(transferStatus.value) &&
    plan.value.productId > 0 &&
    plan.value.qtyBase > 0
)

const listAvailableProductIds = async (locationId: number) => {
  const pageSize = 500
  const availableProductIds = new Set<number>()
  let offset = 0

  while (true) {
    const items = await serialApi.listProductItems({
      location_id: locationId,
      status: 'in_stock',
      limit: pageSize,
      offset
    })
    items
      .filter((item) => item.reserved_transfer_doc_id == null)
      .forEach((item) => availableProductIds.add(item.product_id))
    if (items.length < pageSize) break
    offset += pageSize
  }

  return availableProductIds
}

const loadAvailableProductsByLocation = async (locationId: number) => {
  if (!locationId) {
    products.value = []
    plan.value.productId = 0
    return
  }
  const [productsInLocation, availableProductIds] = await Promise.all([
    productApi.getProducts({ locationId }),
    listAvailableProductIds(locationId)
  ])
  products.value = productsInLocation.filter((product) => availableProductIds.has(product.id))
  if (!products.value.some((product) => product.id === plan.value.productId)) {
    plan.value.productId = 0
  }
}

const createDoc = async () => {
  try {
    const res = await serialApi.createTransfer(fromLocationId.value, toLocationId.value)
    transferId.value = res.id
    pickLog.value = []
    recvLog.value = []
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const refreshTransfer = async () => {
  if (!transferId.value) {
    transferDetail.value = null
    transferStatus.value = ''
    plannedTotal.value = 0
    pickedTotal.value = 0
    receivedTotal.value = 0
    return
  }
  const detail = await serialApi.getTransfer(transferId.value)
  transferDetail.value = detail
  transferStatus.value = detail.status
  plannedTotal.value = detail.planned_count
  pickedTotal.value = detail.picked_count
  receivedTotal.value = detail.received_count
}

const planDoc = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.planTransfer(transferId.value, plan.value.productId, plan.value.qtyBase)
    pickLog.value.unshift(`PLAN line_id=${res.transfer_line_id} planned=${res.planned_items}`)
    await refreshTransfer()
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
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanPicking = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.scanTransfer(transferId.value, scanPickQr.value.trim(), 'picking')
    pickLog.value.unshift(`PICK ${scanPickQr.value.trim()} => ${JSON.stringify(res)}`)
    scanPickQr.value = ''
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const ship = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.shipTransfer(transferId.value)
    pickLog.value.unshift(`SHIP => ${JSON.stringify(res)}`)
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const scanReceiving = async () => {
  if (!transferId.value) return
  try {
    const res = await serialApi.scanTransfer(transferId.value, scanRecvQr.value.trim(), 'receiving')
    recvLog.value.unshift(`RECV ${scanRecvQr.value.trim()} => ${JSON.stringify(res)}`)
    scanRecvQr.value = ''
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const closeDoc = async () => {
  if (!transferId.value) return
  if (!confirm('Закрыть перемещение? Не принятое будет списано как lost_in_transit.')) return
  try {
    const res = await serialApi.closeTransfer(transferId.value)
    recvLog.value.unshift(`CLOSE => ${JSON.stringify(res)}`)
    await refreshTransfer()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  units.value = await productApi.getUnits()
})

watch(fromLocationId, async (locationId) => {
  await loadAvailableProductsByLocation(locationId)
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
  margin: 0;
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
  vertical-align: top;
  font-size: 0.92rem;
}
.qr-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
