<template>
  <div class="page">
    <div class="page-head">
      <h2>Ингредиенты и привязки</h2>
      <div class="actions">
        <button class="btn btn-outline" :disabled="loadingIngredients" @click="loadIngredients">Обновить</button>
      </div>
    </div>

    <div class="card">
      <h3>
        {{ editingIngredientId ? `Редактирование ингредиента #${editingIngredientId}` : 'Создать ингредиент' }}
      </h3>
      <div class="form-grid">
        <label>
          Код *
          <input v-model="ingredientForm.code" class="form-control" placeholder="tomato_paste" />
        </label>
        <label>
          Название *
          <input v-model="ingredientForm.name" class="form-control" placeholder="Томатная паста" />
        </label>
        <label>
          Базовая единица *
          <select v-model.number="ingredientForm.baseUnitId" class="form-control">
            <option :value="0">Выберите единицу</option>
            <option v-for="unit in units" :key="`new-unit-${unit.id}`" :value="unit.id">
              {{ unitLabel(unit.id) }}
            </option>
          </select>
        </label>
        <label>
          Описание
          <input v-model="ingredientForm.description" class="form-control" placeholder="Опционально" />
        </label>
      </div>
      <div class="inline-actions">
        <label class="checkbox">
          <input v-model="ingredientForm.isActive" type="checkbox" />
          Активен
        </label>
        <button
          class="btn btn-primary"
          :disabled="ingredientSaving || !hasPermission('product.write')"
          @click="saveIngredient"
        >
          {{ ingredientSaving ? 'Сохранение...' : (editingIngredientId ? 'Сохранить изменения' : 'Создать ингредиент') }}
        </button>
        <button class="btn btn-outline" :disabled="ingredientSaving" @click="startCreateIngredient">
          Новый
        </button>
      </div>
    </div>

    <div class="layout">
      <div class="card">
        <div class="section-head">
          <h3>Список ингредиентов</h3>
          <input
            v-model="ingredientQuery"
            class="form-control"
            placeholder="Поиск по коду/названию"
          />
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Код</th>
                <th>Название</th>
                <th>База</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="ingredient in ingredients"
                :key="`ingredient-${ingredient.id}`"
                :class="{ selected: ingredient.id === selectedIngredientId }"
                @click="selectIngredient(ingredient.id)"
              >
                <td>{{ ingredient.id }}</td>
                <td>{{ ingredient.code }}</td>
                <td>{{ ingredient.name }}</td>
                <td>{{ unitLabel(ingredient.baseUnitId) }}</td>
                <td>{{ ingredient.isActive ? 'active' : 'inactive' }}</td>
              </tr>
              <tr v-if="!ingredients.length && !loadingIngredients">
                <td colspan="5">Ничего не найдено</td>
              </tr>
              <tr v-if="loadingIngredients">
                <td colspan="5">Загрузка...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="section-head">
          <h3>
            Привязки
            <template v-if="selectedIngredient">
              — {{ selectedIngredient.name }} ({{ selectedIngredient.code }})
            </template>
          </h3>
        </div>

        <div v-if="selectedIngredient" class="binding-filters">
          <label>
            Локация
            <select v-model.number="bindingsLocationId" class="form-control">
              <option :value="0">Все</option>
              <option v-for="location in locations" :key="`filter-loc-${location.id}`" :value="location.id">
                {{ location.name }} ({{ location.code }})
              </option>
            </select>
          </label>
          <label class="checkbox">
            <input v-model="includeInactiveBindings" type="checkbox" />
            Показать неактивные
          </label>
        </div>

        <div v-if="selectedIngredient" class="card card-inner">
          <h4>{{ editingBindingId ? `Редактирование привязки #${editingBindingId}` : 'Добавить привязку' }}</h4>
          <div class="form-grid">
            <label>
              Товар *
              <input
                v-model="bindingProductQuery"
                class="form-control"
                list="ingredient-products-list"
                placeholder="Название товара"
                @input="onBindingProductInput"
              />
            </label>
            <label>
              Коэффициент к базе ингредиента *
              <input
                v-model.number="bindingForm.ratioToIngredientBase"
                class="form-control"
                type="number"
                min="0.000001"
                step="0.000001"
              />
            </label>
            <label>
              Приоритет
              <input v-model.number="bindingForm.priority" class="form-control" type="number" min="0" step="1" />
            </label>
            <label>
              Локация
              <select v-model.number="bindingForm.locationId" class="form-control">
                <option :value="0">Глобально</option>
                <option v-for="location in locations" :key="`new-loc-${location.id}`" :value="location.id">
                  {{ location.name }} ({{ location.code }})
                </option>
              </select>
            </label>
            <label>
              Действует с
              <input v-model="bindingForm.validFrom" class="form-control" type="datetime-local" />
            </label>
            <label>
              Действует до
              <input v-model="bindingForm.validTo" class="form-control" type="datetime-local" />
            </label>
          </div>
          <div class="inline-actions">
            <label class="checkbox">
              <input v-model="bindingForm.isActive" type="checkbox" />
              Активна
            </label>
            <button
              class="btn btn-primary"
              :disabled="bindingSaving || !hasPermission('product.write')"
              @click="saveBinding"
            >
              {{ bindingSaving ? 'Сохранение...' : (editingBindingId ? 'Сохранить привязку' : 'Добавить привязку') }}
            </button>
            <button v-if="editingBindingId" class="btn btn-outline" :disabled="bindingSaving" @click="cancelBindingEdit">
              Отмена
            </button>
          </div>
        </div>

        <div v-if="selectedIngredient" class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Товар</th>
                <th>Коэф.</th>
                <th>Приоритет</th>
                <th>Локация</th>
                <th>Период</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="binding in bindings" :key="`binding-${binding.id}`" :class="{ inactive: !binding.isActive }">
                <td>{{ binding.id }}</td>
                <td>
                  <RouterLink :to="`/product-view/${binding.productId}`">
                    {{ binding.productName || `#${binding.productId}` }}
                  </RouterLink>
                </td>
                <td>{{ binding.ratioToIngredientBase }}</td>
                <td>{{ binding.priority }}</td>
                <td>{{ locationLabel(binding.locationId) }}</td>
                <td>{{ formatPeriod(binding.validFrom, binding.validTo) }}</td>
                <td>{{ binding.isActive ? 'active' : 'inactive' }}</td>
                <td>
                  <button
                    class="btn btn-outline btn-sm"
                    :disabled="!hasPermission('product.write')"
                    @click.stop="startEditBinding(binding)"
                  >
                    Редактировать
                  </button>
                  <button
                    class="btn btn-danger btn-sm"
                    :disabled="deletingBindingId === binding.id || !hasPermission('product.write')"
                    @click.stop="deleteBinding(binding.id)"
                  >
                    {{ deletingBindingId === binding.id ? 'Удаление...' : 'Удалить' }}
                  </button>
                </td>
              </tr>
              <tr v-if="!bindings.length && !loadingBindings">
                <td colspan="8">Привязок нет</td>
              </tr>
              <tr v-if="loadingBindings">
                <td colspan="8">Загрузка...</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="muted">Выберите ингредиент из списка слева.</div>
      </div>
    </div>

    <datalist id="ingredient-products-list">
      <option
        v-for="product in productAutocomplete.productOptions.value"
        :key="`ingredient-product-${product.id}`"
        :value="productAutocomplete.formatProductOption(product)"
      />
    </datalist>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { productApi, type Ingredient, type IngredientBinding, type Location, type Product, type Unit } from '@/api/productApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const ingredients = ref<Ingredient[]>([])
const bindings = ref<IngredientBinding[]>([])
const products = ref<Product[]>([])
const locations = ref<Location[]>([])
const units = ref<Unit[]>([])

const selectedIngredientId = ref<number | null>(null)
const editingIngredientId = ref<number | null>(null)
const editingBindingId = ref<number | null>(null)
const ingredientQuery = ref('')
const bindingProductQuery = ref('')

const loadingIngredients = ref(false)
const loadingBindings = ref(false)
const ingredientSaving = ref(false)
const bindingSaving = ref(false)
const deletingBindingId = ref<number | null>(null)

const includeInactiveBindings = ref(false)
const bindingsLocationId = ref(0)

const ingredientForm = ref({
  code: '',
  name: '',
  baseUnitId: 0,
  description: '',
  isActive: true,
})

const bindingForm = ref({
  productId: 0,
  ratioToIngredientBase: 1,
  priority: 100,
  locationId: 0,
  validFrom: '',
  validTo: '',
  isActive: true,
})

const productAutocomplete = useProductAutocomplete(products, bindingProductQuery, {
  formatOption: (product) => `${product.name} (id=${product.id})`,
})

const selectedIngredient = computed(() => {
  if (!selectedIngredientId.value) return null
  return ingredients.value.find((row) => row.id === selectedIngredientId.value) ?? null
})

const hasPermission = (permission: string) => authStore.hasPermission(permission)

const unitLabel = (unitId?: number | null): string => {
  if (!unitId) return 'Глобально'
  const unit = units.value.find((row) => row.id === unitId)
  if (!unit) return `#${unitId}`
  return unit.description ? `${unit.description} (${unit.code})` : unit.code
}

const locationLabel = (locationId?: number | null): string => {
  if (!locationId) return 'Глобально'
  const location = locations.value.find((row) => row.id === locationId)
  if (!location) return `#${locationId}`
  return `${location.name} (${location.code})`
}

const formatPeriod = (validFrom?: string | null, validTo?: string | null): string => {
  const from = validFrom ? new Date(validFrom).toLocaleString() : '−∞'
  const to = validTo ? new Date(validTo).toLocaleString() : '+∞'
  return `${from} → ${to}`
}

const selectIngredient = (ingredientId: number) => {
  selectedIngredientId.value = ingredientId
}

const onBindingProductInput = () => {
  bindingForm.value.productId = productAutocomplete.parseProductIdFromQuery(bindingProductQuery.value)
}

const toDateTimeLocalInput = (value?: string | null): string => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (raw: number) => String(raw).padStart(2, '0')
  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

const normalizeDateTimeValue = (value: string): string | null => {
  const normalized = value.trim()
  if (!normalized) return null
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return normalized
  return date.toISOString()
}

const resetIngredientForm = () => {
  ingredientForm.value = {
    code: '',
    name: '',
    baseUnitId: 0,
    description: '',
    isActive: true,
  }
}

const startCreateIngredient = () => {
  editingIngredientId.value = null
  resetIngredientForm()
}

const fillIngredientForm = (ingredient: Ingredient) => {
  ingredientForm.value = {
    code: ingredient.code,
    name: ingredient.name,
    baseUnitId: ingredient.baseUnitId,
    description: ingredient.description ?? '',
    isActive: ingredient.isActive,
  }
  editingIngredientId.value = ingredient.id
}

const resetBindingForm = () => {
  bindingForm.value = {
    productId: 0,
    ratioToIngredientBase: 1,
    priority: 100,
    locationId: 0,
    validFrom: '',
    validTo: '',
    isActive: true,
  }
  editingBindingId.value = null
  bindingProductQuery.value = ''
}

const loadIngredients = async () => {
  try {
    loadingIngredients.value = true
    const rows = await productApi.getIngredients(ingredientQuery.value)
    ingredients.value = rows
    if (!rows.length) {
      selectedIngredientId.value = null
      bindings.value = []
      return
    }
    const stillExists = selectedIngredientId.value && rows.some((row) => row.id === selectedIngredientId.value)
    if (!stillExists) {
      const firstRow = rows[0]
      selectedIngredientId.value = firstRow ? firstRow.id : null
    }
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки ингредиентов')
  } finally {
    loadingIngredients.value = false
  }
}

const loadBindings = async () => {
  if (!selectedIngredientId.value) {
    bindings.value = []
    return
  }
  try {
    loadingBindings.value = true
    bindings.value = await productApi.getIngredientBindings(selectedIngredientId.value, {
      locationId: bindingsLocationId.value > 0 ? bindingsLocationId.value : undefined,
      includeInactive: includeInactiveBindings.value,
    })
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки привязок')
  } finally {
    loadingBindings.value = false
  }
}

const saveIngredient = async () => {
  const payload = ingredientForm.value
  if (!payload.code.trim() || !payload.name.trim() || payload.baseUnitId <= 0) {
    alert('Заполните код, название и базовую единицу')
    return
  }
  try {
    ingredientSaving.value = true
    const requestPayload = {
      code: payload.code.trim(),
      name: payload.name.trim(),
      baseUnitId: payload.baseUnitId,
      description: payload.description.trim() || null,
      isActive: payload.isActive,
    }
    if (editingIngredientId.value) {
      await productApi.updateIngredient(editingIngredientId.value, requestPayload)
    } else {
      const created = await productApi.createIngredient(requestPayload)
      selectedIngredientId.value = created.id
    }
    await loadIngredients()
    if (editingIngredientId.value) {
      selectedIngredientId.value = editingIngredientId.value
    }
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка сохранения ингредиента')
  } finally {
    ingredientSaving.value = false
  }
}

const saveBinding = async () => {
  if (!selectedIngredientId.value) {
    alert('Сначала выберите ингредиент')
    return
  }
  bindingForm.value.productId = productAutocomplete.parseProductIdFromQuery(bindingProductQuery.value)
  if (bindingForm.value.productId <= 0 || Number(bindingForm.value.ratioToIngredientBase) <= 0) {
    alert('Выберите товар и задайте коэффициент больше 0')
    return
  }
  try {
    bindingSaving.value = true
    const payload = {
      productId: bindingForm.value.productId,
      ratioToIngredientBase: bindingForm.value.ratioToIngredientBase,
      priority: bindingForm.value.priority,
      locationId: bindingForm.value.locationId > 0 ? bindingForm.value.locationId : null,
      validFrom: normalizeDateTimeValue(bindingForm.value.validFrom),
      validTo: normalizeDateTimeValue(bindingForm.value.validTo),
      isActive: bindingForm.value.isActive,
    }
    if (editingBindingId.value) {
      await productApi.updateIngredientBinding(selectedIngredientId.value, editingBindingId.value, payload)
    } else {
      await productApi.createIngredientBinding(selectedIngredientId.value, payload)
    }
    resetBindingForm()
    await loadBindings()
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка сохранения привязки')
  } finally {
    bindingSaving.value = false
  }
}

const startEditBinding = (binding: IngredientBinding) => {
  editingBindingId.value = binding.id
  bindingForm.value = {
    productId: binding.productId,
    ratioToIngredientBase: Number(binding.ratioToIngredientBase),
    priority: binding.priority,
    locationId: binding.locationId ?? 0,
    validFrom: toDateTimeLocalInput(binding.validFrom),
    validTo: toDateTimeLocalInput(binding.validTo),
    isActive: binding.isActive,
  }
  productAutocomplete.syncQueryBySelectedProductId(binding.productId)
}

const cancelBindingEdit = () => {
  resetBindingForm()
}

const deleteBinding = async (bindingId: number) => {
  if (!selectedIngredientId.value) return
  if (!confirm(`Удалить привязку #${bindingId}?`)) return
  try {
    deletingBindingId.value = bindingId
    await productApi.deleteIngredientBinding(selectedIngredientId.value, bindingId)
    await loadBindings()
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка удаления привязки')
  } finally {
    deletingBindingId.value = null
  }
}

watch(selectedIngredientId, () => {
  resetBindingForm()
  void loadBindings()
})

watch(selectedIngredient, (value) => {
  if (value) {
    fillIngredientForm(value)
  } else {
    editingIngredientId.value = null
    resetIngredientForm()
  }
})

watch([bindingsLocationId, includeInactiveBindings], () => {
  void loadBindings()
})

let ingredientSearchTimer: ReturnType<typeof setTimeout> | null = null
watch(ingredientQuery, () => {
  if (ingredientSearchTimer) clearTimeout(ingredientSearchTimer)
  ingredientSearchTimer = setTimeout(() => {
    void loadIngredients()
  }, 250)
})

onMounted(async () => {
  try {
    const [unitsData, productsData, locationsData] = await Promise.all([
      productApi.getUnits(),
      productApi.getProducts({ limit: 2000 }),
      productApi.getLocations(),
    ])
    units.value = unitsData
    products.value = productsData
    locations.value = locationsData
    await loadIngredients()
  } catch (error: any) {
    alert(error?.response?.data?.detail ?? error?.message ?? 'Ошибка начальной загрузки')
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
  margin-bottom: 16px;
}

.actions {
  display: flex;
  gap: 8px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(340px, 1fr) 2fr;
  gap: 16px;
}

.card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: #fff;
}

.card-inner {
  margin-top: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head .form-control {
  max-width: 260px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
}

.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.92rem;
}

.form-control {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}

.inline-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.table-wrap {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.table tbody tr {
  cursor: pointer;
}

.table tbody tr.selected {
  background: #eff6ff;
}

.table tbody tr.inactive {
  opacity: 0.65;
}

.binding-filters {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 12px;
}

.binding-filters > label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.btn {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  background: #fff;
}

.btn-sm {
  padding: 6px 9px;
  font-size: 0.82rem;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.btn-outline {
  background: #fff;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.muted {
  color: #64748b;
}

@media (max-width: 1180px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
