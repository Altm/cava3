<template>
  <div class="home">
    <h1>👋 Добро пожаловать в систему управления продуктами</h1>
    <p class="subtitle">Выберите раздел для начала работы</p>
    
    <div class="cards-grid">
      <!-- Products 2 Card -->
      <div class="card featured-card" @click="navigateTo('/products2')">
        <div class="card-icon">📦</div>
        <h2>Продукты 2</h2>
        <p>Современный интерфейс управления продуктами</p>
        <ul class="features-list">
          <li>✨ Дробные единицы измерения</li>
          <li>📊 Составные продукты и рецепты</li>
          <li>🔗 Рекурсивные композиции</li>
          <li>🍷 Продажа по бокалам</li>
        </ul>
        <button class="card-button">Открыть →</button>
      </div>

      <!-- Classic Products Card -->
      <div class="card" @click="navigateTo('/product-list')">
        <div class="card-icon">📋</div>
        <h2>Список товаров</h2>
        <p>Классический интерфейс управления товарами</p>
        <button class="card-button">Открыть →</button>
      </div>

      <!-- Sales Card -->
      <div class="card" @click="navigateTo('/sales/list')">
        <div class="card-icon">💰</div>
        <h2>Продажи</h2>
        <p>Управление продажами и чеками</p>
        <button class="card-button">Открыть →</button>
      </div>

      <!-- Prices Card -->
      <div class="card" @click="navigateTo('/prices')">
        <div class="card-icon">🏷️</div>
        <h2>Прайсы</h2>
        <p>Управление ценами и ревизиями</p>
        <button class="card-button">Открыть →</button>
      </div>

      <!-- Lots Card -->
      <div class="card" @click="navigateTo('/lots')">
        <div class="card-icon">📦</div>
        <h2>Партии</h2>
        <p>Управление партиями товаров</p>
        <button class="card-button">Открыть →</button>
      </div>

      <!-- Serial/QR Card -->
      <div class="card" @click="navigateTo('/serial/receipts')">
        <div class="card-icon">📱</div>
        <h2>QR/Serial</h2>
        <p>Приёмка, перемещение, инвентаризация</p>
        <button class="card-button">Открыть →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<style scoped>
.home {
  padding: 2rem;
  text-align: center;
  max-width: 1200px;
  margin: 0 auto;
}

.home h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: #1e293b;
}

.subtitle {
  font-size: 1.1rem;
  color: #64748b;
  margin-bottom: 2rem;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  border-color: #3b82f6;
}

.featured-card {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #3b82f6;
  grid-row: span 2;
}

.card-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.card h2 {
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
  color: #1e293b;
}

.card p {
  color: #64748b;
  margin: 0 0 1rem 0;
  font-size: 0.95rem;
}

.features-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.features-list li {
  padding: 0.25rem 0;
  color: #475569;
  font-size: 0.9rem;
}

.features-list li:before {
  content: '✓ ';
  color: #10b981;
  font-weight: bold;
}

.card-button {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 1rem;
}

.card-button:hover {
  background: #2563eb;
}

.featured-card .card-button {
  background: #2563eb;
}

.featured-card .card-button:hover {
  background: #1d4ed8;
}

@media (max-width: 768px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
  
  .featured-card {
    grid-row: auto;
  }
}
</style>