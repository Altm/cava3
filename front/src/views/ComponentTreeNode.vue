<template>
  <div class="component-tree-node">
    <div 
      class="node-content" 
      :class="{ 'is-cycle': node.isCycle, 'has-children': node.children?.length > 0 }"
      :style="{ paddingLeft: `${level * 24}px` }"
    >
      <!-- Expand/Collapse Button -->
      <button 
        v-if="node.children?.length > 0" 
        @click="toggleExpanded" 
        class="toggle-btn"
        :class="{ expanded: isExpanded }"
      >
        {{ isExpanded ? '▼' : '▶' }}
      </button>
      <span v-else class="toggle-placeholder"></span>

      <!-- Node Icon -->
      <span class="node-icon" :class="node.boundProductIsComposite ? 'composite' : 'simple'">
        {{ node.boundProductIsComposite ? '📦' : '🔹' }}
      </span>

      <!-- Node Info -->
      <div class="node-info">
        <div class="node-header">
          <span class="node-name">{{ node.ingredientName }}</span>
          <span v-if="node.isCycle" class="cycle-badge">⚠️ Цикл</span>
          <span v-if="node.boundProductIsComposite" class="composite-badge">Составной</span>
        </div>
        
        <div class="node-details">
          <span class="detail-item">
            <span class="detail-label">Количество:</span>
            <span class="detail-value">{{ node.quantity }}</span>
          </span>
          <span class="detail-item">
            <span class="detail-label">Единица:</span>
            <span class="detail-value">{{ node.unitCode || '—' }}</span>
          </span>
          <span class="detail-item">
            <span class="detail-label">Доступно:</span>
            <span class="detail-value stock-value" :class="{ 'low-stock': node.availableQuantity < 5 }">
              {{ node.availableQuantity }}
            </span>
          </span>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="node-actions">
        <router-link
          v-if="node.boundProductId"
          :to="`/products2/${node.boundProductId}`"
          class="btn btn-sm btn-outline"
          title="Просмотр связанного продукта"
        >
          👁️
        </router-link>
      </div>
    </div>

    <!-- Children -->
    <div v-if="isExpanded && node.children?.length > 0" class="node-children">
      <ComponentTreeNode
        v-for="(child, index) in node.children"
        :key="index"
        :node="child"
        :level="level + 1"
        :product-id="productId"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ProductComponentTreeNode } from '@/api/productApi2'

defineProps<{
  node: ProductComponentTreeNode
  level: number
  productId: number
}>()

const isExpanded = ref(true)

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.component-tree-node {
  margin: 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: background 0.2s;
}

.node-content:hover {
  background: #f1f5f9;
}

.node-content.is-cycle {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.toggle-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: #e2e8f0;
  color: #475569;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: #cbd5e1;
}

.toggle-btn.expanded {
  background: #3b82f6;
  color: white;
}

.toggle-placeholder {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.node-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.node-icon.composite {
  filter: grayscale(0);
}

.node-icon.simple {
  opacity: 0.7;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.node-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

.cycle-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.composite-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.node-details {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.detail-label {
  color: #64748b;
}

.detail-value {
  font-weight: 600;
  color: #1e293b;
}

.stock-value {
  color: #10b981;
}

.stock-value.low-stock {
  color: #f59e0b;
}

.node-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.node-children {
  margin-top: 8px;
  margin-left: 12px;
  border-left: 2px solid #e2e8f0;
  padding-left: 12px;
}

/* Buttons */
.btn {
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  background: white;
  color: #475569;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-outline {
  background: white;
  color: #475569;
}

.btn-sm {
  padding: 4px 6px;
  font-size: 12px;
}
</style>
