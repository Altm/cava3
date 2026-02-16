<template>
  <div class="page">
    <div class="page-head">
      <h2>Просмотр товара #{{ productId }}</h2>
      <div class="head-actions">
        <RouterLink class="btn btn-outline" to="/product-list">К списку</RouterLink>
        <RouterLink class="btn btn-primary" :to="`/product-form/${productId}`">Редактировать</RouterLink>
      </div>
    </div>

    <div v-if="loading" class="card">Загрузка...</div>
    <div v-else-if="errorText" class="card error">{{ errorText }}</div>

    <template v-else-if="product">
      <div class="grid">
        <div class="card">
          <h3>Основное</h3>
          <div class="meta">
            <div><b>ID:</b> {{ product.id }}</div>
            <div><b>Название:</b> {{ product.name }}</div>
            <div><b>Тип товара:</b> {{ productType?.name ?? '-' }}</div>
            <div><b>Базовая единица:</b> {{ baseUnitLabel }}</div>
            <div><b>Остаток:</b> {{ product.stock }}</div>
            <div><b>Стоимость:</b> {{ product.baseCost }}</div>
            <div><b>Составной:</b> {{ product.isComposite ? 'Да' : 'Нет' }}</div>
            <div><b>Поставщик:</b> {{ product.meta?.vendor ?? '-' }}</div>
            <div><b>Тип (meta):</b> {{ product.meta?.type ?? '-' }}</div>
            <div><b>Теги:</b> {{ product.meta?.tags ?? '-' }}</div>
            <div><b>Штрихкод:</b> {{ product.meta?.variantBarcode ?? '-' }}</div>
          </div>
        </div>

        <div class="card">
          <h3>Фото</h3>
          <div v-if="imageUrl" class="image-wrap">
            <img :src="imageUrl" :alt="product.name" class="product-image" />
          </div>
          <div v-else class="muted">Фото не задано</div>
        </div>
      </div>

      <div class="card">
        <h3>Характеристики</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Код</th>
                <th>Название</th>
                <th>Значение</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="attr in sortedAttributes" :key="attr.id">
                <td>{{ attr.code }}</td>
                <td>{{ attr.name }}</td>
                <td>{{ attributeValue(attr.id) }}</td>
              </tr>
              <tr v-if="!sortedAttributes.length">
                <td colspan="3">Нет характеристик</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card" v-if="product.meta?.bodyHtml || product.meta?.seoTitle || product.meta?.seoDescription">
        <h3>Описание и SEO</h3>
        <div class="meta">
          <div><b>SEO title:</b> {{ product.meta?.seoTitle ?? '-' }}</div>
          <div><b>SEO description:</b> {{ product.meta?.seoDescription ?? '-' }}</div>
        </div>
        <div v-if="product.meta?.bodyHtml" class="body-html" v-html="product.meta.bodyHtml"></div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type AttributeDefinition, type ProductType, type Unit, type ProductView } from '@/api/productApi'

const route = useRoute()
const productId = Number(route.params.id)

const loading = ref(true)
const errorText = ref('')
const product = ref<ProductView | null>(null)
const productTypes = ref<ProductType[]>([])
const units = ref<Unit[]>([])

const productType = computed(() => {
  if (!product.value) return null
  return productTypes.value.find((pt) => pt.id === product.value?.productTypeId) ?? null
})

const sortedAttributes = computed<AttributeDefinition[]>(() => {
  const attrs = productType.value?.attributes ?? []
  return [...attrs].sort((a, b) => a.sortOrder - b.sortOrder)
})

const baseUnitLabel = computed(() => {
  if (!product.value) return '-'
  const unit = units.value.find((u) => u.id === product.value?.baseUnitId)
  if (!unit) return String(product.value.baseUnitId)
  return `${unit.code} (${unit.description})`
})

const attributeMap = computed(() => {
  const map = new Map<number, string>()
  for (const attr of product.value?.attributes ?? []) {
    map.set(attr.productAttributeId, String(attr.value))
  }
  return map
})

const attributeValue = (attributeId: number) => {
  return attributeMap.value.get(attributeId) ?? '-'
}

const imageUrl = computed(() => {
  const raw = product.value?.meta?.image?.trim()
  if (!raw) return ''
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw
  const normalized = raw
    .replace(/^\/app\/public\/images\//, '')
    .replace(/^app\/public\/images\//, '')
    .replace(/^\/+/, '')
  if (normalized.startsWith('images/')) return `/${normalized}`
  return `/images/${normalized}`
})

onMounted(async () => {
  try {
    const [productView, productTypesRes, unitsRes] = await Promise.all([
      productApi.getProductView(productId),
      productApi.getProductTypes(),
      productApi.getUnits()
    ])
    product.value = productView
    productTypes.value = productTypesRes
    units.value = unitsRes
  } catch (e: any) {
    errorText.value = e?.response?.data?.detail ?? e?.message ?? 'Ошибка загрузки товара'
  } finally {
    loading.value = false
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
.head-actions {
  display: flex;
  gap: 8px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.meta {
  display: grid;
  gap: 6px;
}
.image-wrap {
  max-width: 460px;
}
.product-image {
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
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
  background: white;
  color: #111827;
  text-decoration: none;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: white;
}
.btn-outline {
  background: transparent;
}
.error {
  color: #b91c1c;
}
.muted {
  color: #6b7280;
}
.body-html {
  margin-top: 10px;
}
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
