<template>
  <div class="sales-page">
    <div class="page-head">
      <h2>Продажи</h2>
      <RouterLink class="btn btn-outline" to="/sales/list">Список продаж</RouterLink>
    </div>

    <div class="cards-grid">
      <section class="card">
        <h3>По товару</h3>
        <div class="field">
          <label>Товар</label>
          <input
            v-model="productQuery"
            list="sales-products-list"
            placeholder="Название товара"
          />
        </div>
        <div class="field">
          <label>Количество</label>
          <input v-model="productQuantity" type="number" min="0.000001" step="0.000001" />
        </div>
        <div class="field">
          <label>Юнит</label>
          <select v-model.number="productUnitId">
            <option v-for="option in productUnitOptions" :key="option.unitId" :value="option.unitId">
              {{ option.label }}
            </option>
          </select>
        </div>
        <button class="btn" @click="addProductLine">Добавить</button>
      </section>

      <section class="card">
        <h3>По QR единицы</h3>
        <div class="field">
          <label>QR (ITM:...)</label>
          <input v-model.trim="itemQrInput" placeholder="ITM:..." />
        </div>
        <button class="btn" @click="addItemQrLine">Добавить</button>
      </section>

      <section class="card">
        <h3>По QR коробки</h3>
        <div class="field">
          <label>QR (BOX:...)</label>
          <input v-model.trim="boxQrInput" placeholder="BOX:..." />
        </div>
        <small>Коробка продаётся только целиком.</small>
        <button class="btn" @click="addBoxQrLine">Добавить</button>
      </section>

      <section class="card">
        <h3>По бокалам</h3>
        <div class="field">
          <label>Товар</label>
          <input
            v-model="glassProductQuery"
            list="sales-products-list"
            placeholder="Название товара"
          />
        </div>
        <div class="field">
          <label>Количество бокалов</label>
          <input v-model="glassQuantity" type="number" min="1" step="1" />
        </div>
        <div class="field">
          <label>Юнит бокала</label>
          <select v-model.number="glassUnitId">
            <option v-for="option in glassUnitOptions" :key="option.unitId" :value="option.unitId">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>Item QR (опц.)</label>
          <input v-model.trim="glassItemQrCode" placeholder="ITM:..." />
        </div>
        <button class="btn" @click="addGlassLine">Добавить</button>
      </section>
    </div>

    <div class="card">
      <div class="card-head">
        <h3>Корзина продажи</h3>
        <button class="btn btn-danger" :disabled="!cartLines.length" @click="clearCart">Очистить</button>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Тип</th>
            <th>Детали</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(line, index) in cartLines" :key="line.id">
            <td>{{ index + 1 }}</td>
            <td>{{ line.kind }}</td>
            <td>{{ line.display }}</td>
            <td>
              <button class="btn btn-outline" @click="removeLine(index)">Удалить</button>
            </td>
          </tr>
          <tr v-if="!cartLines.length">
            <td colspan="4">Нет добавленных позиций</td>
          </tr>
        </tbody>
      </table>
      <div class="actions">
        <button class="btn btn-primary" :disabled="!cartLines.length || submitting" @click="checkout">
          {{ submitting ? 'Отправка...' : 'Оформить продажу' }}
        </button>
      </div>
    </div>

    <div v-if="checkoutResult" class="card">
      <h3>Результат</h3>
      <div class="result-grid">
        <div><b>Sale ID:</b> {{ checkoutResult.saleId }}</div>
        <div><b>Terminal:</b> {{ checkoutResult.terminalId }}</div>
        <div><b>Location:</b> {{ checkoutResult.locationId }}</div>
        <div><b>Сумма:</b> {{ checkoutResult.totalAmount }}</div>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th>Тип</th>
            <th>Товар</th>
            <th>Кол-во</th>
            <th>Цена</th>
            <th>Сумма</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in checkoutResult.lines" :key="`${line.kind}-${line.productId}-${line.unitId}-${line.totalPrice}`">
            <td>{{ line.kind }}</td>
            <td>{{ line.productName }}</td>
            <td>{{ line.quantity }} {{ line.unitCode }}</td>
            <td>{{ line.unitPrice }}</td>
            <td>{{ line.totalPrice }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <datalist id="sales-products-list">
      <option
        v-for="product in productAutocomplete.productOptions.value"
        :key="product.id"
        :value="productAutocomplete.formatProductOption(product)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { useProductAutocomplete } from '@/composables/useProductAutocomplete'
import {
  productApi,
  type Product,
  type SaleCheckoutLineIn,
  type SaleCheckoutOut,
  type Unit,
} from '@/api/productApi'

interface CartLine {
  id: string
  payload: SaleCheckoutLineIn
  kind: string
  display: string
}

const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const checkoutResult = ref<SaleCheckoutOut | null>(null)
const submitting = ref(false)
const cartLines = ref<CartLine[]>([])

const productQuery = ref('')
const productQuantity = ref('1')
const productUnitId = ref<number | null>(null)

const itemQrInput = ref('')
const boxQrInput = ref('')

const glassProductQuery = ref('')
const glassQuantity = ref('1')
const glassUnitId = ref<number | null>(null)
const glassItemQrCode = ref('')

const productAutocomplete = useProductAutocomplete(products, productQuery, {
  formatOption: (product) => `${product.name} (id=${product.id}, остаток=${product.stock})`,
})
const glassProductAutocomplete = useProductAutocomplete(products, glassProductQuery, {
  formatOption: (product) => `${product.name} (id=${product.id}, остаток=${product.stock})`,
})

const selectedProductId = computed(() => {
  const parsed = productAutocomplete.parseProductIdFromQuery(productQuery.value)
  return parsed > 0 ? parsed : null
})
const selectedGlassProductId = computed(() => {
  const parsed = glassProductAutocomplete.parseProductIdFromQuery(glassProductQuery.value)
  return parsed > 0 ? parsed : null
})

const selectedProduct = computed(() => products.value.find((product) => product.id === selectedProductId.value) || null)
const selectedGlassProduct = computed(() => products.value.find((product) => product.id === selectedGlassProductId.value) || null)

const unitLabel = (unitId: number) => {
  const unit = units.value.find((row) => row.id === unitId)
  return unit ? `${unit.code} (${unit.description})` : `#${unitId}`
}

const productUnitOptions = computed(() => {
  const product = selectedProduct.value
  if (!product) return []
  const rows = [...(product.productUnits || [])]
  rows.sort((left, right) => Number(right.ratioToBase) - Number(left.ratioToBase))
  return rows.map((row) => ({
    unitId: row.unitId,
    label: unitLabel(row.unitId),
  }))
})

const glassUnitOptions = computed(() => {
  const product = selectedGlassProduct.value
  if (!product) return []
  const rows = [...(product.productUnits || [])]
  const portionRows = rows.filter((row) => {
    const unit = units.value.find((entry) => entry.id === row.unitId)
    return unit?.unitType === 'portion'
  })
  const resultRows = portionRows.length ? portionRows : rows.filter((row) => row.unitId === product.baseUnitId)
  resultRows.sort((left, right) => Number(left.ratioToBase) - Number(right.ratioToBase))
  return resultRows.map((row) => ({
    unitId: row.unitId,
    label: unitLabel(row.unitId),
  }))
})

watch(selectedProductId, () => {
  if (!selectedProduct.value) {
    productUnitId.value = null
    return
  }
  if (!productUnitOptions.value.find((option) => option.unitId === productUnitId.value)) {
    productUnitId.value = selectedProduct.value.baseUnitId
  }
})

watch(selectedGlassProductId, () => {
  if (!selectedGlassProduct.value) {
    glassUnitId.value = null
    return
  }
  if (!glassUnitOptions.value.find((option) => option.unitId === glassUnitId.value)) {
    glassUnitId.value = glassUnitOptions.value[0]?.unitId ?? selectedGlassProduct.value.baseUnitId
  }
})

const loadInitialData = async () => {
  try {
    const [productRows, unitRows] = await Promise.all([
      productApi.getProducts({ limit: 2000 }),
      productApi.getUnits(),
    ])
    products.value = productRows
    units.value = unitRows
  } catch (error) {
    console.error('Ошибка загрузки данных продаж:', error)
  }
}

const addProductLine = () => {
  const product = selectedProduct.value
  if (!product) {
    alert('Выберите товар')
    return
  }
  const quantity = Number(productQuantity.value)
  if (!Number.isFinite(quantity) || quantity <= 0) {
    alert('Количество должно быть положительным')
    return
  }
  const unitId = productUnitId.value ?? product.baseUnitId
  cartLines.value.push({
    id: `${Date.now()}-${Math.random()}`,
    kind: 'product',
    payload: {
      kind: 'product',
      productId: product.id,
      quantity,
      unitId,
    },
    display: `${product.name}: ${quantity} ${unitLabel(unitId)}`,
  })
}

const addItemQrLine = () => {
  if (!itemQrInput.value) {
    alert('Введите QR единицы')
    return
  }
  cartLines.value.push({
    id: `${Date.now()}-${Math.random()}`,
    kind: 'item_qr',
    payload: {
      kind: 'item_qr',
      qrCode: itemQrInput.value,
    },
    display: itemQrInput.value,
  })
  itemQrInput.value = ''
}

const addBoxQrLine = () => {
  if (!boxQrInput.value) {
    alert('Введите QR коробки')
    return
  }
  cartLines.value.push({
    id: `${Date.now()}-${Math.random()}`,
    kind: 'box_qr',
    payload: {
      kind: 'box_qr',
      qrCode: boxQrInput.value,
      quantity: 1,
    },
    display: boxQrInput.value,
  })
  boxQrInput.value = ''
}

const addGlassLine = () => {
  const product = selectedGlassProduct.value
  if (!product) {
    alert('Выберите товар для бокалов')
    return
  }
  const quantity = Number(glassQuantity.value)
  if (!Number.isInteger(quantity) || quantity <= 0) {
    alert('Количество бокалов должно быть целым положительным')
    return
  }
  const unitId = glassUnitId.value ?? glassUnitOptions.value[0]?.unitId ?? product.baseUnitId
  cartLines.value.push({
    id: `${Date.now()}-${Math.random()}`,
    kind: 'glass',
    payload: {
      kind: 'glass',
      productId: product.id,
      quantity,
      unitId,
      itemQrCode: glassItemQrCode.value || undefined,
    },
    display: `${product.name}: ${quantity} ${unitLabel(unitId)}${glassItemQrCode.value ? `, item=${glassItemQrCode.value}` : ''}`,
  })
  glassItemQrCode.value = ''
}

const removeLine = (index: number) => {
  cartLines.value.splice(index, 1)
}

const clearCart = () => {
  cartLines.value = []
}

const checkout = async () => {
  if (!cartLines.value.length || submitting.value) return
  submitting.value = true
  try {
    checkoutResult.value = await productApi.checkoutSales({
      lines: cartLines.value.map((line) => line.payload),
    })
    cartLines.value = []
    await loadInitialData()
  } catch (error: any) {
    console.error('Ошибка оформления продажи:', error)
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка оформления продажи')
  } finally {
    submitting.value = false
  }
}

onMounted(loadInitialData)
</script>

<style scoped>
.sales-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  background: #fff;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  padding: 0.5rem 0.4rem;
}

.btn {
  border: 1px solid #1f6feb;
  background: #1f6feb;
  color: #fff;
  border-radius: 6px;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline {
  background: #fff;
  color: #1f2937;
  border-color: #d1d5db;
}

.btn-danger {
  background: #ef4444;
  border-color: #ef4444;
}

.btn-primary {
  background: #16a34a;
  border-color: #16a34a;
}

.actions {
  margin-top: 0.75rem;
  display: flex;
  justify-content: flex-end;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.4rem 1rem;
  margin-bottom: 0.75rem;
}

@media (max-width: 1024px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
