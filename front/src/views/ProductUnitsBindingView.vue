<template>
  <div class="page">
    <div class="page-head">
      <h2>Связь продукта и дробной части</h2>
      <RouterLink class="btn btn-outline" to="/product-list">К списку товаров</RouterLink>
    </div>

    <div class="card">
      <div class="form-row">
        <div class="form-group">
          <label>Поиск товара</label>
          <input
            v-model="query"
            class="form-control"
            list="product-units-products"
            placeholder="Название товара"
          />
        </div>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Товар</th>
              <th>Базовая единица</th>
              <th>Крупная единица</th>
              <th>Дробная единица</th>
              <th>Дробных в 1 крупной</th>
              <th>Коэф. дробной</th>
              <th>Статус</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td>{{ unitLabel(row.baseUnitId) }}</td>
              <td>
                <select
                  v-model.number="ensureEditor(row).bottleUnitId"
                  class="form-control"
                  @change="onBottleOrGlassChanged(row)"
                >
                  <option :value="0">Выберите</option>
                  <option v-for="unit in bottleOptions(row)" :key="`bottle-${row.id}-${unit.id}`" :value="unit.id">
                    {{ unitLabel(unit.id) }}
                  </option>
                </select>
              </td>
              <td>
                <select
                  v-model.number="ensureEditor(row).glassUnitId"
                  class="form-control"
                  @change="onBottleOrGlassChanged(row)"
                >
                  <option :value="0">Выберите</option>
                  <option v-for="unit in glassOptions(row)" :key="`glass-${row.id}-${unit.id}`" :value="unit.id">
                    {{ unitLabel(unit.id) }}
                  </option>
                </select>
              </td>
              <td>
                <input
                  v-model.number="ensureEditor(row).glassesInBottle"
                  type="number"
                  min="1"
                  step="1"
                  class="form-control"
                />
              </td>
              <td>
                <span>{{ previewGlassRatio(row) }}</span>
              </td>
              <td>
                <span v-if="!glassOptions(row).length" class="muted">Нет доступных дробных юнитов</span>
                <span v-else-if="!hasValidEditor(row)" class="muted">Заполните поля</span>
                <span v-else class="ok">Готово</span>
              </td>
              <td>
                <button
                  class="btn btn-primary"
                  :disabled="ensureEditor(row).saving || !hasValidEditor(row)"
                  @click="saveGlassLink(row)"
                >
                  {{ ensureEditor(row).saving ? 'Сохранение...' : 'Сохранить' }}
                </button>
                <RouterLink class="btn btn-outline" :to="`/product-form/${row.id}#product-units`">
                  Расширенно
                </RouterLink>
                <RouterLink class="btn btn-outline" :to="`/product-view/${row.id}`">
                  Просмотр
                </RouterLink>
              </td>
            </tr>
            <tr v-if="!filteredRows.length && !loading">
              <td colspan="10">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="10">Загрузка...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <datalist id="product-units-products">
      <option
        v-for="row in productAutocomplete.productOptions.value"
        :key="row.id"
        :value="productAutocomplete.formatProductOption(row)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { productApi, type Product, type ProductUnit, type Unit } from '@/api/productApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'

interface GlassLinkEditor {
  bottleUnitId: number
  glassUnitId: number
  glassesInBottle: number
  saving: boolean
}

const loading = ref(false)
const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const query = ref('')
const editors = ref<Record<number, GlassLinkEditor>>({})

const productAutocomplete = useProductAutocomplete(products, query, {
  formatOption: (product) => `${product.name} (id=${product.id})`,
})

const filteredRows = computed(() => {
  const normalized = query.value.trim().toLowerCase()
  if (!normalized) return products.value
  return products.value.filter((row) => row.name.toLowerCase().includes(normalized))
})

const unitLabel = (unitId: number) => {
  const unit = units.value.find((row) => row.id === unitId)
  if (!unit) return `#${unitId}`
  return unit.description ? `${unit.description} (${unit.code})` : unit.code
}

const unitById = computed(() => {
  const map = new Map<number, Unit>()
  for (const unit of units.value) map.set(unit.id, unit)
  return map
})

const sortedUnits = (product: Product): ProductUnit[] => {
  const rows = [...(product.productUnits || [])]
  return rows.sort((left, right) => Number(right.ratioToBase) - Number(left.ratioToBase))
}

const ratioToBase = (product: Product, unitId: number): number | null => {
  if (unitId === product.baseUnitId) return 1
  const row = (product.productUnits || []).find((entry) => Number(entry.unitId) === Number(unitId))
  if (!row) return null
  return Number(row.ratioToBase)
}

const bottleOptions = (product: Product): Unit[] => {
  const ids = new Set<number>([product.baseUnitId])
  for (const row of sortedUnits(product)) ids.add(Number(row.unitId))
  const options = [...ids]
    .map((id) => unitById.value.get(id))
    .filter((row): row is Unit => !!row)
  return options.sort((a, b) => a.code.localeCompare(b.code))
}

const glassOptions = (product: Product): Unit[] => {
  const editor = editors.value[product.id]
  const selectedParentUnitId = editor?.bottleUnitId ?? product.baseUnitId
  const parentRatio = ratioToBase(product, selectedParentUnitId)
  const ids = new Set<number>()
  for (const row of sortedUnits(product)) {
    const ratio = Number(row.ratioToBase)
    if (!Number.isFinite(ratio) || ratio <= 0) continue
    if (parentRatio && ratio >= parentRatio) continue
    ids.add(Number(row.unitId))
  }
  const fromProduct = [...ids]
    .map((id) => unitById.value.get(id))
    .filter((row): row is Unit => !!row)
    .sort((a, b) => a.code.localeCompare(b.code))
  if (fromProduct.length) return fromProduct
  return units.value
    .filter((row) => row.id !== selectedParentUnitId)
    .sort((a, b) => a.code.localeCompare(b.code))
}

const estimateGlassesInBottle = (product: Product, bottleUnitId: number, glassUnitId: number): number => {
  const bottleRatio = ratioToBase(product, bottleUnitId)
  const glassRatio = ratioToBase(product, glassUnitId)
  if (!bottleRatio || !glassRatio || glassRatio <= 0) return 5
  const raw = bottleRatio / glassRatio
  if (!Number.isFinite(raw) || raw <= 0) return 5
  return Math.max(1, Math.round(raw))
}

const ensureEditor = (product: Product): GlassLinkEditor => {
  const current = editors.value[product.id]
  if (current) return current
  const bottleId = bottleOptions(product)[0]?.id ?? product.baseUnitId
  const glassId = glassOptions(product)[0]?.id ?? 0
  const editor: GlassLinkEditor = {
    bottleUnitId: bottleId,
    glassUnitId: glassId,
    glassesInBottle: glassId ? estimateGlassesInBottle(product, bottleId, glassId) : 5,
    saving: false,
  }
  editors.value[product.id] = editor
  return editor
}

const onBottleOrGlassChanged = (product: Product) => {
  const editor = ensureEditor(product)
  if (!editor.bottleUnitId || !editor.glassUnitId) return
  editor.glassesInBottle = estimateGlassesInBottle(product, editor.bottleUnitId, editor.glassUnitId)
}

const hasValidEditor = (product: Product): boolean => {
  const editor = ensureEditor(product)
  return editor.bottleUnitId > 0 && editor.glassUnitId > 0 && Number.isInteger(editor.glassesInBottle) && editor.glassesInBottle > 0
}

const previewGlassRatio = (product: Product): string => {
  const editor = ensureEditor(product)
  if (!hasValidEditor(product)) return '-'
  const bottleRatio = ratioToBase(product, editor.bottleUnitId)
  if (!bottleRatio || bottleRatio <= 0) return '-'
  const ratio = bottleRatio / editor.glassesInBottle
  return `${ratio.toFixed(6)} к базе`
}

const saveGlassLink = async (product: Product) => {
  const editor = ensureEditor(product)
  if (!hasValidEditor(product)) {
    alert('Заполните связь корректно')
    return
  }
  try {
    editor.saving = true
    const updated = await productApi.updateProductFractionLink(product.id, {
      bottleUnitId: editor.bottleUnitId,
      glassUnitId: editor.glassUnitId,
      glassesInBottle: editor.glassesInBottle,
      glassDiscreteStep: 1,
    })
    const row = products.value.find((entry) => entry.id === product.id)
    if (row) {
      row.productUnits = updated.productUnits || []
    }
    editor.glassesInBottle = updated.glassesInBottle
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка сохранения связи')
  } finally {
    editor.saving = false
  }
}

const loadData = async () => {
  try {
    loading.value = true
    const [productsResponse, unitsResponse] = await Promise.all([
      productApi.getProducts({ limit: 2000 }),
      productApi.getUnits(),
    ])
    products.value = productsResponse
    units.value = unitsResponse
    editors.value = {}
    for (const row of products.value) {
      ensureEditor(row)
    }
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page {
  padding: 20px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

.form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
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
  border-bottom: 1px solid #eee;
  padding: 8px;
  text-align: left;
  vertical-align: top;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: #fff;
  color: #111827;
  text-decoration: none;
  margin-right: 6px;
}

.btn-outline {
  background: #fff;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
}

.muted {
  color: #6b7280;
}

.ok {
  color: #15803d;
  font-weight: 600;
}
</style>
