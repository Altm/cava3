<template>
  <div class="page">
    <div class="page-head">
      <h2>Редактирование приёмки #{{ receiptId }}</h2>
      <div class="head-actions">
        <RouterLink class="btn btn-outline" :to="`/serial/boxes/manage?receipt_id=${receiptId}`">Управление коробками</RouterLink>
        <RouterLink class="btn btn-outline" to="/serial/receipts/list">К списку</RouterLink>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Документ</h3>
        <div class="meta" v-if="receipt">
          <div><b>Статус:</b> {{ receipt.status }}</div>
          <div><b>Локация:</b> {{ locationLabel(receipt.to_location_id) }}</div>
          <div><b>Создан:</b> {{ formatDate(receipt.created_at) }}</div>
        </div>
        <div class="form-actions">
          <button class="btn btn-outline" :disabled="!canGenerate" @click="generate">Сгенерировать</button>
          <button class="btn btn-outline" :disabled="!canPost" @click="postDoc">Подтвердить</button>
          <button class="btn btn-danger" :disabled="!canVoid" @click="voidDoc">Отменить</button>
          <button class="btn btn-primary" @click="reload">Обновить</button>
        </div>
      </div>

      <div class="card">
        <h3>Добавить строку</h3>
        <div class="form-group">
          <label>Товар</label>
          <input
            v-model="lineProductQuery"
            list="receipt-edit-products-line-list"
            class="form-control"
            :disabled="!canEditLines"
            placeholder="Начните вводить название товара"
            @input="syncLineProductByQuery"
          />
          <small v-if="line.productId" class="hint">Выбран product_id={{ line.productId }}</small>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Количество (в базовой единице)</label>
            <input v-model="line.qty" class="form-control" :disabled="!canEditLines" />
          </div>
          <div class="form-group">
            <label>Unit ID (авто: базовая)</label>
            <input :value="baseUnitIdForLine" class="form-control" disabled />
          </div>
        </div>
        <div class="form-group">
          <label>Партия поставщика (опц)</label>
          <input v-model="line.supplierLotNumber" class="form-control" :disabled="!canEditLines" />
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" :disabled="!canAddLine" @click="addLine">Добавить строку</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Строки приёмки</h3>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Товар</th>
              <th>Qty</th>
              <th>Unit</th>
              <th>Партия поставщика</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in lines" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ productLabel(row.product_id) }}</td>
              <td>{{ row.qty }}</td>
              <td>{{ row.unit_id }}</td>
              <td>{{ row.supplier_lot_number ?? '-' }}</td>
              <td>
                <button class="btn btn-danger" :disabled="!canEditLines" @click="removeLine(row.id)">Удалить</button>
              </td>
            </tr>
            <tr v-if="!lines.length">
              <td colspan="6">Нет строк</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h3>Печать этикеток ITM</h3>
      <div class="form-actions">
        <button class="btn btn-primary" :disabled="!canLoadLabels" @click="loadLabels">Получить список QR</button>
        <button class="btn btn-outline" :disabled="!labels.length" @click="copyLabels">Скопировать</button>
      </div>
      <p v-if="receipt?.status === 'draft'" class="hint">Сначала нажмите «Сгенерировать», затем получите список QR.</p>
      <pre v-if="labels.length" class="pre">{{ labels.join('\n') }}</pre>
    </div>

    <div class="card">
      <h3>Автоматическая упаковка в коробки</h3>
      <p class="hint">
        Можно запускать несколько раз с разным количеством в коробке — для разных форматов коробок.
      </p>
      <div class="form-row">
        <div class="form-group">
          <label>Количество в коробке</label>
          <input v-model="autoBox.itemsPerBox" class="form-control" placeholder="например 6" />
        </div>
        <div class="form-group">
          <label>Лимит коробок (опц)</label>
          <input v-model="autoBox.maxBoxes" class="form-control" placeholder="например 3" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Товар (опц)</label>
          <input
            v-model="autoBoxProductQuery"
            list="receipt-edit-products-auto-list"
            class="form-control"
            placeholder="Все товары из приёмки"
            @input="syncAutoBoxProductByQuery"
          />
          <small v-if="autoBox.productId" class="hint">Выбран product_id={{ autoBox.productId }}</small>
        </div>
        <div class="form-group">
          <label>Lot ID (опц)</label>
          <input v-model="autoBox.lotId" class="form-control" placeholder="например 125" />
        </div>
      </div>
      <div class="form-actions">
        <label><input v-model="autoBox.includePartial" type="checkbox" /> Создавать неполную коробку</label>
        <label><input v-model="autoBox.sealFullBoxes" type="checkbox" /> Полные коробки закрывать</label>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" :disabled="!canAutoBox" @click="runAutoBox">Автосоздать коробки</button>
        <button class="btn btn-outline" :disabled="!autoBoxResult?.boxes?.length" @click="copyAutoBoxLabels">Скопировать QR коробок</button>
      </div>
      <div v-if="autoBoxResult" class="meta">
        <div><b>Создано коробок:</b> {{ autoBoxResult.boxes_created }}</div>
        <div><b>Упаковано бутылок:</b> {{ autoBoxResult.items_packed }}</div>
        <div><b>Осталось без коробки:</b> {{ autoBoxResult.items_remaining_unboxed }}</div>
      </div>
      <pre v-if="autoBoxResult?.boxes?.length" class="pre">{{ autoBoxResult.boxes.map((b) => `${b.qr_code} | items=${b.packed_items} | sealed=${b.sealed}`).join('\n') }}</pre>
    </div>

    <datalist id="receipt-edit-products-line-list">
      <option
        v-for="p in lineAutocomplete.productOptions.value"
        :key="`line-${p.id}`"
        :value="lineAutocomplete.formatProductOption(p)"
      />
    </datalist>
    <datalist id="receipt-edit-products-auto-list">
      <option
        v-for="p in autoBoxAutocomplete.productOptions.value"
        :key="`auto-${p.id}`"
        :value="autoBoxAutocomplete.formatProductOption(p)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type ReceiptAutoBoxOut, type ReceiptDetailOut, type ReceiptLineOut } from '@/api/serialApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'

const route = useRoute()
const receiptId = Number(route.params.id)

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const receipt = ref<ReceiptDetailOut | null>(null)
const lines = ref<ReceiptLineOut[]>([])
const labels = ref<string[]>([])
const autoBoxResult = ref<ReceiptAutoBoxOut | null>(null)
const autoBox = ref({
  itemsPerBox: '6',
  maxBoxes: '',
  productId: 0,
  lotId: '',
  includePartial: true,
  sealFullBoxes: true,
})

const line = ref({
  productId: 0,
  qty: '1',
  supplierLotNumber: ''
})
const lineProductQuery = ref('')
const autoBoxProductQuery = ref('')

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => !!baseUnitsById.get(p.baseUnitId)?.isDiscrete)
})
const lineAutocomplete = useProductAutocomplete(serialProducts, lineProductQuery)
const autoBoxAutocomplete = useProductAutocomplete(serialProducts, autoBoxProductQuery)

const baseUnitIdForLine = computed(() => {
  const product = products.value.find((x) => x.id === line.value.productId)
  return product?.baseUnitId ?? ''
})

const canEditLines = computed(() => receipt.value?.status === 'draft')
const canAddLine = computed(() => canEditLines.value && line.value.productId > 0 && Number(line.value.qty) > 0 && !!baseUnitIdForLine.value)
const canGenerate = computed(() => receipt.value?.status === 'draft')
const canPost = computed(() => receipt.value?.status === 'generated')
const canVoid = computed(() => receipt.value != null && ['draft', 'generated', 'posted'].includes(receipt.value.status))
const canLoadLabels = computed(() => receipt.value != null && ['generated', 'posted'].includes(receipt.value.status))
const canAutoBox = computed(() => receipt.value != null && ['generated', 'posted'].includes(receipt.value.status))

const syncLineProductByQuery = () => {
  line.value.productId = lineAutocomplete.parseProductIdFromQuery(lineProductQuery.value)
}

const syncAutoBoxProductByQuery = () => {
  autoBox.value.productId = autoBoxAutocomplete.parseProductIdFromQuery(autoBoxProductQuery.value)
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

const productLabel = (productId: number) => {
  const product = products.value.find((p) => p.id === productId)
  return product ? `${product.name} (${productId})` : String(productId)
}

const reload = async () => {
  try {
    receipt.value = await serialApi.getReceipt(receiptId)
    lines.value = await serialApi.listReceiptLines(receiptId)
    autoBoxResult.value = null
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const addLine = async () => {
  try {
    const unitId = Number(baseUnitIdForLine.value)
    await serialApi.addReceiptLine(receiptId, line.value.productId, line.value.qty, unitId, line.value.supplierLotNumber || undefined)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const removeLine = async (lineId: number) => {
  if (!confirm(`Удалить строку #${lineId}?`)) return
  try {
    await serialApi.removeReceiptLine(receiptId, lineId)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const generate = async () => {
  try {
    const res = await serialApi.generateReceipt(receiptId)
    alert(`Сгенерировано: lots=${res.lots_created}, items=${res.items_created}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const postDoc = async () => {
  try {
    const res = await serialApi.postReceipt(receiptId)
    alert(`Подтверждено: items=${res.posted_items}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const voidDoc = async () => {
  if (!confirm('Отменить приёмку?')) return
  try {
    const res = await serialApi.voidReceipt(receiptId)
    alert(`Отменено: voided_items=${res.voided_items ?? 0}`)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const loadLabels = async () => {
  try {
    const res = await serialApi.receiptItemLabels(receiptId)
    labels.value = res.labels
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const copyLabels = async () => {
  try {
    await navigator.clipboard.writeText(labels.value.join('\n'))
  } catch {
    alert('Не удалось скопировать')
  }
}

const runAutoBox = async () => {
  const itemsPerBox = Number(autoBox.value.itemsPerBox)
  if (!Number.isInteger(itemsPerBox) || itemsPerBox <= 0) {
    alert('Количество в коробке должно быть целым положительным числом')
    return
  }
  const maxBoxesRaw = autoBox.value.maxBoxes.trim()
  const maxBoxes = maxBoxesRaw ? Number(maxBoxesRaw) : undefined
  if (maxBoxes !== undefined && (!Number.isInteger(maxBoxes) || maxBoxes <= 0)) {
    alert('Лимит коробок должен быть целым положительным числом')
    return
  }
  const lotIdRaw = autoBox.value.lotId.trim()
  const lotId = lotIdRaw ? Number(lotIdRaw) : undefined
  if (lotId !== undefined && (!Number.isInteger(lotId) || lotId <= 0)) {
    alert('Lot ID должен быть целым положительным числом')
    return
  }
  try {
    autoBoxResult.value = await serialApi.receiptAutoBox(receiptId, {
      items_per_box: itemsPerBox,
      max_boxes: maxBoxes,
      include_partial: autoBox.value.includePartial,
      seal_full_boxes: autoBox.value.sealFullBoxes,
      product_id: autoBox.value.productId > 0 ? autoBox.value.productId : undefined,
      lot_id: lotId,
    })
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
  }
}

const copyAutoBoxLabels = async () => {
  if (!autoBoxResult.value?.boxes?.length) return
  const text = autoBoxResult.value.boxes.map((box) => box.qr_code).join('\n')
  try {
    await navigator.clipboard.writeText(text)
    alert('QR коробок скопированы')
  } catch {
    alert('Не удалось скопировать')
  }
}

onMounted(async () => {
  locations.value = await productApi.getLocations()
  products.value = await productApi.getProducts()
  units.value = await productApi.getUnits()
  await reload()
})

watch(
  () => line.value.productId,
  (productId) => {
    lineAutocomplete.syncQueryBySelectedProductId(productId)
  }
)

watch(
  () => autoBox.value.productId,
  (productId) => {
    autoBoxAutocomplete.syncQueryBySelectedProductId(productId)
  }
)
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
.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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
.pre {
  white-space: pre-wrap;
  background: #f7f7f7;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.hint {
  color: #4b5563;
  margin-top: 8px;
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
