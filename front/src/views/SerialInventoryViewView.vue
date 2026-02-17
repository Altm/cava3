<template>
  <div class="page">
    <div class="page-head">
      <h2>Просмотр инвентаризации #{{ inventoryId }}</h2>
      <RouterLink class="btn btn-outline" to="/serial/inventories/list">К списку</RouterLink>
    </div>

    <div v-if="result" class="card">
      <div><b>Статус:</b> {{ result.status }}</div>
      <div><b>Локация:</b> {{ locationLabel(result.location_id) }}</div>
      <div>
        <b>Учтено:</b> {{ result.accounted_items.length }} item, {{ result.accounted_boxes.length }} box
        /
        <b>Не учтено:</b> {{ result.unaccounted_items.length }} item, {{ result.unaccounted_boxes.length }} box
      </div>
    </div>

    <div v-if="result" class="grid">
      <div class="card">
        <h3>Учтено</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Box QR</th>
                <th>Статус</th>
                <th>Счёт</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="box in result.accounted_boxes" :key="`acc-box-${box.box_id}`" class="row-ok">
                <td>{{ box.box_qr_code }}</td>
                <td>{{ box.status }}</td>
                <td>{{ box.counted_items }}/{{ box.total_items }}</td>
              </tr>
              <tr v-if="!result.accounted_boxes.length">
                <td colspan="3">Нет учтённых коробок</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Item QR</th>
                <th>Box QR</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.accounted_items" :key="`acc-item-${item.product_item_id}`" class="row-ok">
                <td>{{ item.product_item_id }}</td>
                <td>{{ item.product_name }}</td>
                <td>{{ item.product_item_qr_code }}</td>
                <td>{{ item.box_qr_code || '-' }}</td>
              </tr>
              <tr v-if="!result.accounted_items.length">
                <td colspan="4">Нет учтённых item</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <h3>Не учтено</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Box QR</th>
                <th>Статус</th>
                <th>Счёт</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="box in result.unaccounted_boxes" :key="`miss-box-${box.box_id}`" class="row-bad">
                <td>{{ box.box_qr_code }}</td>
                <td>{{ box.status }}</td>
                <td>{{ box.counted_items }}/{{ box.total_items }}</td>
              </tr>
              <tr v-if="!result.unaccounted_boxes.length">
                <td colspan="3">Нет неучтённых коробок</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Item QR</th>
                <th>Box QR</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.unaccounted_items" :key="`miss-item-${item.product_item_id}`" class="row-bad">
                <td>{{ item.product_item_id }}</td>
                <td>{{ item.product_name }}</td>
                <td>{{ item.product_item_qr_code }}</td>
                <td>{{ item.box_qr_code || '-' }}</td>
              </tr>
              <tr v-if="!result.unaccounted_items.length">
                <td colspan="4">Нет неучтённых item</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { productApi, type Location } from '@/api/productApi'
import { serialApi, type InventoryResultOut } from '@/api/serialApi'

const route = useRoute()
const inventoryId = Number(route.params.id)
const result = ref<InventoryResultOut | null>(null)
const locations = ref<Location[]>([])

const locationLabel = (locationId: number) => {
  const location = locations.value.find((l) => l.id === locationId)
  return location ? `${location.name} (${location.code})` : String(locationId)
}

onMounted(async () => {
  try {
    locations.value = await productApi.getLocations()
    result.value = await serialApi.getInventoryResult(inventoryId)
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка')
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
.btn-outline {
  background: transparent;
}
.table-wrap {
  overflow: auto;
  margin-top: 12px;
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
.row-ok {
  background: #ecfdf5;
}
.row-bad {
  background: #fef2f2;
}
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
