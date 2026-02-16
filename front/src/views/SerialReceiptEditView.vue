<template>
  <div class="page">
    <div class="page-head">
      <h2>Редактирование приёмки #{{ receiptId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/receipts/list">К списку</RouterLink>
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
          <select v-model.number="line.productId" class="form-control" :disabled="!canEditLines">
            <option :value="0">Выберите товар</option>
            <option v-for="p in serialProducts" :key="p.id" :value="p.id">{{ p.name }} (id={{ p.id }})</option>
          </select>
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
        <button class="btn btn-primary" @click="loadLabels">Получить список QR</button>
        <button class="btn btn-outline" :disabled="!labels.length" @click="copyLabels">Скопировать</button>
      </div>
      <pre v-if="labels.length" class="pre">{{ labels.join('\n') }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location, type Product, type Unit } from '@/api/productApi'
import { serialApi, type ReceiptDetailOut, type ReceiptLineOut } from '@/api/serialApi'

const route = useRoute()
const receiptId = Number(route.params.id)

const locations = ref<Location[]>([])
const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const receipt = ref<ReceiptDetailOut | null>(null)
const lines = ref<ReceiptLineOut[]>([])
const labels = ref<string[]>([])

const line = ref({
  productId: 0,
  qty: '1',
  supplierLotNumber: ''
})

const serialProducts = computed(() => {
  const baseUnitsById = new Map(units.value.map((u) => [u.id, u]))
  return products.value.filter((p) => !!baseUnitsById.get(p.baseUnitId)?.isDiscrete)
})

const baseUnitIdForLine = computed(() => {
  const product = products.value.find((x) => x.id === line.value.productId)
  return product?.baseUnitId ?? ''
})

const canEditLines = computed(() => receipt.value?.status === 'draft')
const canAddLine = computed(() => canEditLines.value && line.value.productId > 0 && Number(line.value.qty) > 0 && !!baseUnitIdForLine.value)
const canGenerate = computed(() => receipt.value?.status === 'draft')
const canPost = computed(() => receipt.value?.status === 'generated')
const canVoid = computed(() => receipt.value != null && ['draft', 'generated', 'posted'].includes(receipt.value.status))

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
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
