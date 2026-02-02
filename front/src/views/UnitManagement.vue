<template>
  <div class="unit-management">
    <h2>Управление единицами измерения</h2>

    <div class="actions">
      <button v-if="hasPermission('unit.write')" @click="showCreateDialog" class="btn btn-primary">Создать единицу измерения</button>
    </div>

    <table v-if="units.length > 0" class="unit-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Код</th>
          <th>Описание</th>
          <th>Тип</th>
          <th>Дискретная</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="unit in units" :key="unit.id">
          <td>{{ unit.id }}</td>
          <td>{{ unit.code }}</td>
          <td>{{ unit.description }}</td>
          <td>{{ unit.unitType }}</td>
          <td>{{ unit.isDiscrete ? 'Да' : 'Нет' }}</td>
          <td>
            <button v-if="hasPermission('unit.write')" @click="editUnit(unit)" class="btn btn-sm">Редактировать</button>
            <button v-if="hasPermission('unit.delete')" @click="deleteUnit(unit.id)" class="btn btn-sm btn-danger">Удалить</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="no-data">
      Нет единиц измерения
    </div>

    <!-- Modal for creating/editing unit -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h3>{{ editingUnit ? 'Редактировать единицу измерения' : 'Создать единицу измерения' }}</h3>
        <form @submit.prevent="saveUnit">
          <div class="form-group">
            <label>Код *</label>
            <input v-model="form.code" required class="form-control" />
          </div>
          
          <div class="form-group">
            <label>Описание *</label>
            <input v-model="form.description" required class="form-control" />
          </div>
          
          <div class="form-group">
            <label>Тип *</label>
            <select v-model="form.unitType" required class="form-control">
              <option value="">Выберите тип</option>
              <option value="base">Базовая</option>
              <option value="package">Упаковка</option>
              <option value="portion">Порция</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="form.isDiscrete" />
              Дискретная
            </label>
          </div>
          
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">{{ editingUnit ? 'Обновить' : 'Создать' }}</button>
            <button type="button" @click="closeModal" class="btn btn-outline">Отмена</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { productApi } from '@/api/productApi'
import type { Unit } from '@/api/productApi'
import { useAuthStore } from '@/stores/auth'

// State
const units = ref<Unit[]>([])
const showModal = ref(false)
const editingUnit = ref<Unit | null>(null)

const form = ref({
  id: 0,
  code: '',
  description: '',
  unitType: 'base' as 'base' | 'package' | 'portion',
  isDiscrete: true
})

// Auth store for permissions
const authStore = useAuthStore()

// Check permissions
const hasPermission = (permission: string) => {
  return authStore.hasPermission(permission)
}

// Methods
const loadUnits = async () => {
  try {
    units.value = await productApi.getUnits()
  } catch (error) {
    console.error('Error loading units:', error)
  }
}

const showCreateDialog = () => {
  editingUnit.value = null
  form.value = {
    id: 0,
    code: '',
    description: '',
    unitType: 'base',
    isDiscrete: true
  }
  showModal.value = true
}

const editUnit = (unit: Unit) => {
  editingUnit.value = unit
  form.value = {
    id: unit.id,
    code: unit.code,
    description: unit.description || '',
    unitType: unit.unitType as 'base' | 'package' | 'portion',
    isDiscrete: unit.isDiscrete
  }
  showModal.value = true
}

const deleteUnit = async (id: number) => {
  if (!confirm('Вы уверены, что хотите удалить эту единицу измерения?')) {
    return
  }
  
  try {
    await productApi.deleteUnit(id) // Предполагаем, что API метод будет добавлен
    await loadUnits()
  } catch (error) {
    console.error('Error deleting unit:', error)
  }
}

const saveUnit = async () => {
  try {
    if (editingUnit.value) {
      // Update existing unit
      await productApi.updateUnit(form.value.id, {
        code: form.value.code,
        description: form.value.description,
        unit_type: form.value.unitType,
        is_discrete: form.value.isDiscrete
      })
    } else {
      // Create new unit
      await productApi.createUnit({
        code: form.value.code,
        description: form.value.description,
        unit_type: form.value.unitType,
        is_discrete: form.value.isDiscrete
      })
    }
    
    closeModal()
    await loadUnits()
  } catch (error) {
    console.error('Error saving unit:', error)
  }
}

const closeModal = () => {
  showModal.value = false
  editingUnit.value = null
}

// Lifecycle
onMounted(() => {
  loadUnits()
})
</script>

<style scoped>
.unit-management {
  padding: 20px;
}

.actions {
  margin-bottom: 20px;
}

.unit-table {
  width: 100%;
  border-collapse: collapse;
}

.unit-table th,
.unit-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.unit-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #666;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 4px;
  width: 500px;
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.tag {
  display: inline-block;
  padding: 2px 6px;
  margin: 2px;
  background-color: #e0e0e0;
  border-radius: 4px;
  font-size: 0.8em;
}

.tag-success {
  background-color: #d4edda;
  color: #155724;
}

.tag-info {
  background-color: #d1ecf1;
  color: #0c5460;
}
</style>