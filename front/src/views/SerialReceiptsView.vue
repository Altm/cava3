<template>
  <div class="page">
    <div class="page-head">
      <h2>Приёмка (QR)</h2>
      <RouterLink class="btn btn-outline" to="/serial/receipts/list">Таблица приёмок</RouterLink>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>

        <div class="form-group">
          <label>Склад (локация)</label>
          <select v-model.number="toLocationId" class="form-control">
            <option :value="0">Выберите локацию</option>
            <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.name }} ({{ l.code }})</option>
          </select>
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!toLocationId" @click="createReceipt">Создать</button>
          <button class="btn btn-outline" :disabled="!receiptId" @click="generate">Сгенерировать</button>
          <button class="btn btn-outline" :disabled="!receiptId" @click="post">Подтвердить</button>
          <button class="btn btn-danger" :disabled="!receiptId" @click="voidDoc">Отменить</button>
        </div>

        <div v-if="receiptId" class="meta">
          <div><b>ID:</b> {{ receiptId }}</div>
          <div><b>Статус:</b> {{ receiptStatus }}</div>
        </div>
      </div>

      <div class="card">
        <h3>Строка приёмки</h3>

        <div class="form-group">
          <label>Товар</label>
          <select v-model.number="line.productId" class="form-control">
            <option :value="0">Выберите товар</option>
            <option v-for="p in serialProducts" :key="p.id" :value="p.id">
              {{ p.name }} (id={{ p.id }})
            </option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Количество (в базовой единице)</label>
            <input v-model="line.qty" class="form-control" placeholder="например 12" />
          </div>
          <div class="form-group">
            <label>Unit ID (авто: базовая)</label>
            <input :value="baseUnitIdForLine" class="form-control" disabled />
          </div>
        </div>

        <div class="form-group">
          <label>Партия поставщика (опц)</label>
          <input v-model="line.supplierLotNumber" class="form-control" />
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!canAddLine" @click="addLine">Добавить строку</button>
        </div>

        <div v-if="lines.length" class="list">
          <div v-for="l in lines" :key="l.id" class="list-item">
            <div>line#{{ l.id }}: product={{ l.product_id }}, qty={{ l.qty }}, unit={{ l.unit_id }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Печать этикеток ITM</h3>
      <div class="form-actions">
        <button class="btn btn-primary" :disabled="!receiptId" @click="loadLabels">Получить список QR</button>
      </div>
      <div v-if="labels.length" class="labels">
        <div class="labels-actions">
          <button class="btn btn-outline" @click="copyLabels">Скопировать</button>
        </div>
        <pre class="pre">{{ labels.join('\n') }}</pre>
      </div>
    </div>

    <div class="card">
      <h3>Коробки (1 продукт, 1 партия)</h3>
      <p class="hint">
        Чтобы создать коробку, отсканируйте одну бутылку (ITM) — система определит product/lot/location, затем нажмите
        “Создать коробку”. Для частичного отбора sealed коробка будет автоматически открыта при pick.
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
        <button class="btn btn-outline" :disabled="!boxId" @click="sealBox">Закрыть (seal)</button>
        <button class="btn btn-outline" :disabled="!boxId" @click="openBox">Открыть</button>
        <button class="btn btn-outline" :disabled="!boxId" @click="loadBoxLabel">QR коробки</button>
      </div>

      <div v-if="boxId" class="meta">
        <div><b>box_id:</b> {{ boxId }}</div>
        <div><b>box_qr:</b> {{ boxQr }}</div>
        <div><b>sealed:</b> {{ boxSealed }}</div>
      </div>

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

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type ReceiptLineOut, type ScanOut } from '@/api/serialApi'

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])

const toLocationId = ref<number>(0)
const receiptId = ref<number | null>(null)
const receiptStatus = ref<string>('')
const lines = ref<ReceiptLineOut[]>([])
const labels = ref<string[]>([])

const line = ref({
  productId: 0,
  qty: '1',
  supplierLotNumber: ''
})

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => {
    const u = baseUnitsById.get(p.baseUnitId)
    return !!u?.isDiscrete
  })
})

const baseUnitIdForLine = computed(() => {
  const p = products.value.find((x) => x.id === line.value.productId)
  return p?.baseUnitId ?? ''
})

const canAddLine = computed(() => {
  return !!receiptId.value && !!line.value.productId && !!line.value.qty && Number(line.value.qty) > 0 && !!baseUnitIdForLine.value
})

const createReceipt = async () => {
  try {
    const res = await serialApi.createReceipt(toLocationId.value)
    receiptId.value = res.id
    receiptStatus.value = res.status
    lines.value = []
    labels.value = []
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const addLine = async () => {
  if (!receiptId.value) return
  try {
    const unitId = Number(baseUnitIdForLine.value)
    const res = await serialApi.addReceiptLine(receiptId.value, line.value.productId, line.value.qty, unitId, line.value.supplierLotNumber || undefined)
    lines.value.push(res)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const generate = async () => {
  if (!receiptId.value) return
  try {
    const res = await serialApi.generateReceipt(receiptId.value)
    receiptStatus.value = 'generated'
    alert(`Сгенерировано: lots=${res.lots_created}, items=${res.items_created}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const post = async () => {
  if (!receiptId.value) return
  try {
    const res = await serialApi.postReceipt(receiptId.value)
    receiptStatus.value = 'posted'
    alert(`Подтверждено: items=${res.posted_items}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const voidDoc = async () => {
  if (!receiptId.value) return
  if (!confirm('Отменить приёмку? QR будут погашены (voided).')) return
  try {
    const res = await serialApi.voidReceipt(receiptId.value)
    receiptStatus.value = 'void'
    alert(`Отменено: voided_items=${res.voided_items ?? 0}`)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const loadLabels = async () => {
  if (!receiptId.value) return
  try {
    const res = await serialApi.receiptItemLabels(receiptId.value)
    labels.value = res.labels
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const copyLabels = async () => {
  try {
    await navigator.clipboard.writeText(labels.value.join('\n'))
    alert('Скопировано')
  } catch {
    alert('Не удалось скопировать')
  }
}

// Boxes
const boxCtxQr = ref('')
const boxCtx = ref<ScanOut | null>(null)
const boxId = ref<number | null>(null)
const boxQr = ref<string>('')
const boxSealed = ref<boolean | null>(null)
const addToBoxQr = ref('')
const boxAddLog = ref<string[]>([])

const resolveBoxCtx = async () => {
  try {
    const res = await serialApi.scanQr(boxCtxQr.value.trim())
    if (!res.found || res.kind !== 'ITM') {
      throw new Error('Нужен ITM')
    }
    if (!res.product_id || !res.lot_id || !res.location_id) {
      throw new Error('Скан не вернул product_id/lot_id/location_id (обновите backend scan)')
    }
    boxCtx.value = res
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const createBox = async () => {
  if (!boxCtx.value) return
  try {
    const res = await serialApi.createBox(boxCtx.value.product_id!, boxCtx.value.lot_id!, boxCtx.value.location_id!, false)
    boxId.value = res.id
    boxQr.value = res.qr_code
    boxSealed.value = res.sealed
    boxAddLog.value = []
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const openBox = async () => {
  if (!boxId.value) return
  try {
    const res = await serialApi.openBox(boxId.value)
    boxSealed.value = res.sealed
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const sealBox = async () => {
  if (!boxId.value) return
  try {
    const res = await serialApi.sealBox(boxId.value)
    boxSealed.value = res.sealed
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
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
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
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
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
  font-size: 0.95rem;
  color: #111827;
}
.list {
  margin-top: 10px;
  border-top: 1px dashed #ddd;
  padding-top: 10px;
}
.list-item {
  padding: 6px 0;
  border-bottom: 1px dashed #eee;
}
.labels {
  margin-top: 12px;
}
.labels-actions {
  margin-bottom: 8px;
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
  margin-top: -8px;
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
