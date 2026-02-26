<template>
  <div class="page">
    <div class="page-head">
      <h2>История рецептов: {{ history?.productName ?? `Товар #${productId}` }}</h2>
      <div class="head-actions">
        <RouterLink class="btn btn-outline" :to="`/product-view/${productId}`">К товару</RouterLink>
        <RouterLink class="btn btn-outline" to="/product-list">К списку</RouterLink>
      </div>
    </div>

    <div class="card filters">
      <div class="filters-grid">
        <label>
          Дата действия
          <input v-model="filters.activeDate" type="date" class="form-control" />
        </label>
        <label>
          Дата начала (с)
          <input v-model="filters.dateFrom" type="date" class="form-control" />
        </label>
        <label>
          Дата начала (по)
          <input v-model="filters.dateTo" type="date" class="form-control" />
        </label>
      </div>
      <div class="filters-actions">
        <button class="btn btn-primary" @click="loadHistory">Применить</button>
        <button class="btn btn-outline" @click="resetFilters">Сбросить</button>
      </div>
    </div>

    <div v-if="loading" class="card">Загрузка...</div>
    <div v-else-if="errorText" class="card error">{{ errorText }}</div>

    <template v-else>
      <div v-if="!history?.versions?.length" class="card muted">
        Версии рецепта не найдены по текущим фильтрам.
      </div>

      <div v-for="version in history?.versions ?? []" :key="version.id" class="card">
        <div class="version-head">
          <div>
            <h3>Версия {{ version.version }}</h3>
            <div class="version-meta">
              <span>ID: {{ version.id }}</span>
              <span>Активна: {{ version.isActive ? 'Да' : 'Нет' }}</span>
              <span>Период: {{ formatDateTime(version.validFrom) }} — {{ version.validTo ? formatDateTime(version.validTo) : 'по настоящее время' }}</span>
              <span>Создал: {{ version.createdBy ?? '-' }}</span>
            </div>
          </div>
          <div class="components-count">Компонентов: {{ version.components.length }}</div>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Компонент</th>
                <th>Количество</th>
                <th>Единица</th>
                <th>Потери</th>
                <th>Замены</th>
                <th>Округление</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="component in version.components" :key="component.id">
                <td>{{ component.ingredientName }} ({{ component.ingredientCode }}, #{{ component.ingredientId }})</td>
                <td>{{ component.quantity }}</td>
                <td>{{ component.unitCode }} (#{{ component.unitId }})</td>
                <td>{{ component.wasteFactor }}</td>
                <td>{{ component.substitutionAllowed ? 'Да' : 'Нет' }}</td>
                <td>{{ component.rounding ?? '-' }}</td>
              </tr>
              <tr v-if="!version.components.length">
                <td colspan="6">Компоненты отсутствуют</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type ProductRecipeHistoryOut } from '@/api/productApi'

const route = useRoute()
const productId = computed(() => Number(route.params.id))

const loading = ref(false)
const errorText = ref('')
const history = ref<ProductRecipeHistoryOut | null>(null)
const filters = ref({
  activeDate: '',
  dateFrom: '',
  dateTo: '',
})

const toDateStart = (value: string): string | undefined => {
  if (!value) return undefined
  return `${value}T00:00:00`
}

const toDateEnd = (value: string): string | undefined => {
  if (!value) return undefined
  return `${value}T23:59:59`
}

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString()
}

const loadHistory = async () => {
  loading.value = true
  errorText.value = ''
  try {
    history.value = await productApi.getProductRecipeHistory(productId.value, {
      activeAt: toDateStart(filters.value.activeDate),
      dateFrom: toDateStart(filters.value.dateFrom),
      dateTo: toDateEnd(filters.value.dateTo),
    })
  } catch (error: any) {
    errorText.value = error?.response?.data?.detail ?? error?.message ?? 'Ошибка загрузки истории рецептов'
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value.activeDate = ''
  filters.value.dateFrom = ''
  filters.value.dateTo = ''
  loadHistory()
}

onMounted(loadHistory)

watch(
  () => route.params.id,
  () => {
    loadHistory()
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
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: #fff;
}
.filters-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 10px;
}
.filters-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.92rem;
}
.filters-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.form-control {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px;
}
.version-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.version-head h3 {
  margin: 0 0 6px;
}
.version-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #334155;
  font-size: 0.9rem;
}
.components-count {
  font-weight: 600;
  color: #0f172a;
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
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: #fff;
  color: #111827;
  text-decoration: none;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.btn-outline {
  background: transparent;
}
.error {
  color: #b91c1c;
}
.muted {
  color: #64748b;
}
@media (max-width: 1024px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }
}
</style>
