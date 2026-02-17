<template>
  <div class="page">
    <div class="page-head">
      <h2>Привязка юнитов к товарам</h2>
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
              <th>Привязанные юниты</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.name }}</td>
              <td>{{ unitLabel(row.baseUnitId) }}</td>
              <td>
                <div class="chips">
                  <span
                    v-for="unit in sortedUnits(row)"
                    :key="`${row.id}-${unit.unitId}`"
                    class="chip"
                  >
                    {{ unitLabel(unit.unitId) }} × {{ unit.ratioToBase }}
                  </span>
                  <span v-if="!row.productUnits?.length" class="muted">Нет</span>
                </div>
              </td>
              <td>
                <RouterLink class="btn btn-outline" :to="`/product-form/${row.id}#product-units`">
                  Редактировать
                </RouterLink>
                <RouterLink class="btn btn-outline" :to="`/product-view/${row.id}`">
                  Просмотр
                </RouterLink>
              </td>
            </tr>
            <tr v-if="!filteredRows.length && !loading">
              <td colspan="5">Нет данных</td>
            </tr>
            <tr v-if="loading">
              <td colspan="5">Загрузка...</td>
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

import { productApi, type Product, type Unit } from '@/api/productApi'
import { useProductAutocomplete } from '@/composables/useProductAutocomplete'

const loading = ref(false)
const products = ref<Product[]>([])
const units = ref<Unit[]>([])
const query = ref('')

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

const sortedUnits = (product: Product) => {
  const rows = [...(product.productUnits || [])]
  return rows.sort((left, right) => Number(right.ratioToBase) - Number(left.ratioToBase))
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
</style>
