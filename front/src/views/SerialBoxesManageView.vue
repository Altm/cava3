<template>
  <div class="page">
    <div class="page-head">
      <h2>Коробки (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/scan/boxes">Таблица коробок</RouterLink>
    </div>

    <div v-if="receiptIdQuery" class="card">
      <div class="meta"><b>Контекст приёмки:</b> #{{ receiptIdQuery }}</div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Создание коробки</h3>
        <p class="hint">
          Отсканируйте бутылку `ITM:...` для контекста (product/lot/location), затем создайте коробку.
        </p>
        <div class="form-row">
          <div class="form-group">
            <label>Скан ITM для контекста</label>
            <input v-model="boxCtxQr" class="form-control" placeholder="ITM:..." />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-outline" @click="resolveBoxCtx">Определить</button>
          </div>
        </div>
        <div v-if="boxCtx" class="meta">
          <div><b>product_id:</b> {{ boxCtx.product_id }}</div>
          <div><b>lot_id:</b> {{ boxCtx.lot_id }}</div>
          <div><b>location_id:</b> {{ boxCtx.location_id }}</div>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!boxCtx" @click="createBox">Создать коробку (open)</button>
        </div>
      </div>

      <div class="card">
        <h3>Редактирование коробки</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Box ID</label>
            <input v-model.number="boxIdInput" type="number" min="1" class="form-control" />
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button class="btn btn-outline" :disabled="!boxIdInput" @click="loadBoxById">Загрузить</button>
          </div>
        </div>
        <div v-if="boxId" class="meta">
          <div><b>box_id:</b> {{ boxId }}</div>
          <div><b>box_qr:</b> {{ boxQr }}</div>
          <div><b>status:</b> {{ boxStatus }}</div>
          <div><b>sealed:</b> {{ boxSealed }}</div>
          <div><b>quantity:</b> {{ boxQuantity }}</div>
          <div><b>product:</b> {{ productLabel(boxProductId) }}</div>
          <div><b>location:</b> {{ locationLabel(boxLocationId) }}</div>
        </div>
        <div class="form-actions">
          <button class="btn btn-outline" :disabled="!boxId" @click="openBox">Открыть</button>
          <button class="btn btn-outline" :disabled="!boxId" @click="sealBox">Закрыть (seal)</button>
          <button class="btn btn-outline" :disabled="!boxId" @click="loadBoxLabel">QR коробки</button>
          <button class="btn btn-primary" :disabled="!boxId" @click="refreshCurrentBox">Обновить</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Добавить бутылку в коробку</h3>
      <div class="form-row">
        <div class="form-group">
          <label>Скан ITM в коробку</label>
          <input v-model="addToBoxQr" class="form-control" placeholder="ITM:..." />
        </div>
        <div class="form-group">
          <label>&nbsp;</label>
          <button class="btn btn-primary" :disabled="!boxId" @click="addItemToBox">Добавить</button>
        </div>
      </div>

      <div v-if="boxAddLog.length" class="labels">
        <pre class="pre">{{ boxAddLog.join('\n') }}</pre>
      </div>
    </div>

    <div class="card">
      <h3>Содержимое коробки</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>QR</th>
              <th>Статус</th>
              <th>Lot</th>
              <th>Локация</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in boxItems" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.qr_code }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.lot_id }}</td>
              <td>{{ locationLabel(item.location_id) }}</td>
            </tr>
            <tr v-if="!boxItems.length">
              <td colspan="5">Нет данных</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location, type Product } from '@/api/productApi'
import { serialApi, type ProductItemListOut, type ScanOut } from '@/api/serialApi'

const route = useRoute()
const receiptIdQuery = Number(route.query.receipt_id || 0) || null

const locations = ref<Location[]>([])
const products = ref<Product[]>([])

const boxCtxQr = ref('')
const boxCtx = ref<ScanOut | null>(null)

const boxIdInput = ref<number | null>(Number(route.query.box_id || 0) || null)
const boxId = ref<number | null>(null)
const boxQr = ref('')
const boxSealed = ref<boolean | null>(null)
const boxStatus = ref('')
const boxQuantity = ref<number>(0)
const boxProductId = ref<number | null>(null)
const boxLocationId = ref<number | null>(null)

const addToBoxQr = ref('')
const boxAddLog = ref<string[]>([])
const boxItems = ref<ProductItemListOut[]>([])

const locationLabel = (locationId: number | null | undefined) => {
  if (!locationId) return '-'
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const productLabel = (productId: number | null | undefined) => {
  if (!productId) return '-'
  const product = products.value.find((p) => p.id === productId)
  return product ? `${product.name} (${productId})` : String(productId)
}

const loadBoxItems = async () => {
  if (!boxId.value) {
    boxItems.value = []
    return
  }
  boxItems.value = await serialApi.listProductItems({ box_id: boxId.value, limit: 500 })
}

const setCurrentBox = async (box: {
  id: number
  qr_code: string
  quantity: number
  sealed: boolean
  status: string
  product_id: number
  location_id: number
}) => {
  boxId.value = box.id
  boxIdInput.value = box.id
  boxQr.value = box.qr_code
  boxSealed.value = box.sealed
  boxStatus.value = box.status
  boxQuantity.value = box.quantity
  boxProductId.value = box.product_id
  boxLocationId.value = box.location_id
  await loadBoxItems()
}

const loadBoxById = async () => {
  if (!boxIdInput.value) return
  try {
    const box = await serialApi.getBox(boxIdInput.value)
    await setCurrentBox(box)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const resolveBoxCtx = async () => {
  try {
    const res = await serialApi.scanQr(boxCtxQr.value.trim())
    if (!res.found || res.kind !== 'ITM') throw new Error('Нужен ITM')
    if (!res.product_id || !res.lot_id || !res.location_id) throw new Error('Скан не вернул product_id/lot_id/location_id')
    boxCtx.value = res
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const createBox = async () => {
  if (!boxCtx.value) return
  try {
    const box = await serialApi.createBox(boxCtx.value.product_id!, boxCtx.value.lot_id!, boxCtx.value.location_id!, false)
    boxAddLog.value = []
    await setCurrentBox(box)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const refreshCurrentBox = async () => {
  if (!boxId.value) return
  try {
    const box = await serialApi.getBox(boxId.value)
    await setCurrentBox(box)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const openBox = async () => {
  if (!boxId.value) return
  try {
    const box = await serialApi.openBox(boxId.value)
    await setCurrentBox(box)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const sealBox = async () => {
  if (!boxId.value) return
  try {
    const box = await serialApi.sealBox(boxId.value)
    await setCurrentBox(box)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const loadBoxLabel = async () => {
  if (!boxId.value) return
  try {
    const res = await serialApi.boxLabels(boxId.value)
    alert(res.labels.join('\n'))
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const addItemToBox = async () => {
  if (!boxId.value) return
  try {
    const res = await serialApi.addItemToBox(boxId.value, addToBoxQr.value.trim())
    boxAddLog.value.unshift(`+ item_id=${res.product_item_id}`)
    addToBoxQr.value = ''
    await loadBoxItems()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
  if (boxIdInput.value) {
    await loadBoxById()
  }
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
.meta {
  margin-top: 12px;
}
.hint {
  color: #4b5563;
}
.labels {
  margin-top: 12px;
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
