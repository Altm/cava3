<template>
  <div class="page">
    <div class="page-head">
      <h2>Управление прайсами</h2>
      <div class="head-actions">
        <RouterLink class="btn btn-outline" to="/prices/list">Список прайсов</RouterLink>
        <RouterLink class="btn btn-outline" to="/lots">Партии</RouterLink>
      </div>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Локация</label>
          <select v-model.number="form.locationId" class="form-control" @change="onLocationChanged">
            <option :value="0">Выберите локацию</option>
            <option v-for="location in locations" :key="location.id" :value="location.id">
              {{ location.name }} ({{ location.code }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Название ревизии</label>
          <input v-model.trim="form.name" class="form-control" placeholder="Например: Бар +5%" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Режим</label>
          <select v-model="form.mode" class="form-control">
            <option value="percent">Процент на все товары</option>
            <option value="fixed">Фиксированная добавка</option>
            <option value="calculator">Файл-калькулятор</option>
          </select>
        </div>
        <div class="form-group">
          <label>Валюта</label>
          <input v-model.trim="form.currency" maxlength="3" class="form-control" placeholder="EUR / USD" />
        </div>
      </div>
      <div v-if="form.mode === 'percent'" class="form-row">
        <div class="form-group">
          <label>Процент (например 5)</label>
          <input v-model.trim="form.percentDelta" class="form-control" inputmode="decimal" />
        </div>
      </div>
      <div v-if="form.mode === 'fixed'" class="form-row">
        <div class="form-group">
          <label>Добавка в валюте (например 10)</label>
          <input v-model.trim="form.amountDelta" class="form-control" inputmode="decimal" />
        </div>
      </div>
      <template v-if="form.mode === 'calculator'">
        <div class="form-row">
          <div class="form-group">
            <label>Файл калькулятора</label>
            <select v-model="form.calculatorFile" class="form-control">
              <option value="">Выберите файл</option>
              <option v-for="file in calculatorFiles" :key="file" :value="file">{{ file }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Класс</label>
            <select v-model="form.calculatorClass" class="form-control">
              <option value="">Выберите класс</option>
              <option v-for="calculator in filteredCalculators" :key="`${calculator.file}:${calculator.className}`" :value="calculator.className">
                {{ calculator.className }} — {{ calculator.description || '-' }}
              </option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group full">
            <label>Параметры (JSON)</label>
            <textarea
              v-model="form.calculatorParamsJson"
              class="form-control"
              rows="4"
              placeholder='{"multiplier":"1.05","offset":"0"}'
            />
          </div>
        </div>
      </template>

      <div class="form-actions">
        <button class="btn btn-primary" :disabled="saving || !form.locationId" @click="createRevision">Создать новый прайс</button>
        <button class="btn btn-outline" :disabled="saving || !form.locationId" @click="createQuickPercent">+5% на все товары</button>
        <button class="btn btn-outline" :disabled="saving || !form.locationId" @click="createQuickFixed">+10 в валюте на все товары</button>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <h3>Текущий прайс</h3>
        <button class="btn btn-outline" :disabled="!form.locationId" @click="loadCurrent">Обновить</button>
      </div>
      <div v-if="currentPrice">
        <div class="meta">
          <span><b>Локация:</b> {{ currentPrice.locationName || currentPrice.locationId }}</span>
          <span><b>Ревизия:</b> {{ currentPrice.revisionId ?? '-' }}</span>
          <span><b>Название:</b> {{ currentPrice.revisionName ?? '-' }}</span>
          <span><b>Создана:</b> {{ formatDate(currentPrice.revisionCreatedAt) }}</span>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Товар</th>
                <th>Unit</th>
                <th>Base Price</th>
                <th>Средняя закупка</th>
                <th>Валюта</th>
                <th>Цена</th>
                <th>Партии</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in currentPrice.items" :key="`curr-${item.productId}-${item.unitId}`">
                <td>{{ item.productName }}</td>
                <td>{{ item.unitCode }}</td>
                <td>{{ item.basePrice ?? '-' }}</td>
                <td>{{ item.averagePurchaseCost ?? '-' }}</td>
                <td>{{ item.currency }}</td>
                <td>{{ item.amount }}</td>
                <td>
                  <button class="btn btn-outline" :disabled="!(item.lots?.length)" @click="openLots(item)">
                    Партии ({{ item.lots?.length ?? 0 }})
                  </button>
                </td>
              </tr>
              <tr v-if="!currentPrice.items.length">
                <td colspan="7">Прайс пуст</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="selectedLots" class="card">
      <div class="card-head">
        <h3>Партии по товару: {{ selectedLots.productName }}</h3>
        <button class="btn btn-outline" @click="selectedLots = null">Закрыть</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Lot ID</th>
              <th>Supplier Lot</th>
              <th>Дата партии</th>
              <th>Закупка</th>
              <th>В наличии (item)</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="lot in selectedLots.lots" :key="`lot-${lot.lotId}`">
              <td>{{ lot.lotId }}</td>
              <td>{{ lot.supplierLotNumber || '-' }}</td>
              <td>{{ formatDate(lot.receivedAt) }}</td>
              <td>{{ lot.purchasePrice ?? '-' }}</td>
              <td>{{ lot.inStockItems }}</td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/lots/${lot.lotId}`">Содержимое</RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  productApi,
  type CurrentPriceOut,
  type Location,
  type PriceCalculatorInfo,
  type PriceRevisionItem,
  type PriceRevisionMode,
} from '@/api/productApi'

const locations = ref<Location[]>([])
const calculators = ref<PriceCalculatorInfo[]>([])
const currentPrice = ref<CurrentPriceOut | null>(null)
const selectedLots = ref<{ productName: string; lots: NonNullable<PriceRevisionItem['lots']> } | null>(null)

const saving = ref(false)

const form = ref({
  locationId: 0,
  name: '',
  mode: 'percent' as PriceRevisionMode,
  currency: 'EUR',
  percentDelta: '5',
  amountDelta: '10',
  calculatorFile: '',
  calculatorClass: '',
  calculatorParamsJson: '{"multiplier":"1.00","offset":"0"}',
})

const calculatorFiles = computed(() => {
  return [...new Set(calculators.value.map((row) => row.file))]
})

const filteredCalculators = computed(() => {
  if (!form.value.calculatorFile) return calculators.value
  return calculators.value.filter((row) => row.file === form.value.calculatorFile)
})

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const parseCalculatorParams = () => {
  const raw = form.value.calculatorParamsJson?.trim()
  if (!raw) return {}
  const parsed = JSON.parse(raw)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('JSON параметров должен быть объектом')
  }
  return parsed as Record<string, any>
}

const loadCurrent = async () => {
  if (!form.value.locationId) {
    currentPrice.value = null
    return
  }
  currentPrice.value = await productApi.getCurrentPrices(form.value.locationId)
}

const openLots = (item: PriceRevisionItem) => {
  selectedLots.value = {
    productName: item.productName,
    lots: item.lots ?? [],
  }
}

const createRevision = async () => {
  if (!form.value.locationId) {
    alert('Выберите локацию')
    return
  }
  try {
    saving.value = true
    const payload: any = {
      locationId: form.value.locationId,
      name: form.value.name || undefined,
      mode: form.value.mode,
      currency: form.value.currency || undefined,
    }

    if (form.value.mode === 'percent') {
      payload.percentDelta = form.value.percentDelta
    } else if (form.value.mode === 'fixed') {
      payload.amountDelta = form.value.amountDelta
    } else {
      payload.calculatorFile = form.value.calculatorFile
      payload.calculatorClass = form.value.calculatorClass
      payload.calculatorParams = parseCalculatorParams()
    }

    const created = await productApi.createPriceRevision(payload)
    if (created.items.length) {
      openLots(created.items[0])
    } else {
      selectedLots.value = null
    }
    await loadCurrent()
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка создания прайса')
  } finally {
    saving.value = false
  }
}

const createQuickPercent = async () => {
  form.value.mode = 'percent'
  form.value.percentDelta = '5'
  await createRevision()
}

const createQuickFixed = async () => {
  form.value.mode = 'fixed'
  form.value.amountDelta = '10'
  await createRevision()
}

const onLocationChanged = async () => {
  selectedLots.value = null
  await loadCurrent()
}

onMounted(async () => {
  try {
    const [loadedLocations, loadedCalculators] = await Promise.all([
      productApi.getLocations(),
      productApi.getPriceCalculators(),
    ])
    locations.value = loadedLocations
    calculators.value = loadedCalculators
    if (!form.value.locationId && locations.value.length) {
      form.value.locationId = locations.value[0].id
    }
    if (!form.value.calculatorFile && calculators.value.length) {
      form.value.calculatorFile = calculators.value[0].file
      form.value.calculatorClass = calculators.value[0].className
    }
    await loadCurrent()
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка инициализации страницы прайсов')
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
  margin-bottom: 12px;
}
.head-actions {
  display: flex;
  gap: 8px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group.full {
  grid-column: 1 / span 2;
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
.meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
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
  .form-row {
    grid-template-columns: 1fr;
  }
  .form-group.full {
    grid-column: auto;
  }
}
</style>
