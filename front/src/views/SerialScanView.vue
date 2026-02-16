<template>
  <div class="page">
    <h2>Сканер QR</h2>

    <form class="card" @submit.prevent="handleScan">
      <div class="form-group">
        <label>QR (ITM:... или BOX:...)</label>
        <input v-model="qr" placeholder="ITM:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" class="form-control" />
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit">Сканировать</button>
        <button class="btn btn-outline" type="button" @click="reset">Очистить</button>
      </div>
    </form>

    <div v-if="result" class="card">
      <h3>Результат</h3>
      <pre class="pre">{{ JSON.stringify(result, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { serialApi } from '@/api/serialApi'

const qr = ref('')
const result = ref<any>(null)

const handleScan = async () => {
  try {
    result.value = await serialApi.scanQr(qr.value.trim())
  } catch (e: any) {
    console.error(e)
    alert(e?.response?.data?.detail ?? e?.message ?? 'Ошибка сканирования')
  }
}

const reset = () => {
  qr.value = ''
  result.value = null
}
</script>

<style scoped>
.page {
  padding: 20px;
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
.form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.form-actions {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: white;
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
.pre {
  white-space: pre-wrap;
  background: #f7f7f7;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
</style>

