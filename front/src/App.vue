<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { logout } from '@/api/authApi'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore();
authStore.initializeAuth();

const handleLogout = () => {
  logout();
  authStore.logout();
  // Redirect to login page
  window.location.href = '/login';
};
</script>

<template>
  <header>
    <nav>
      <template v-if="authStore.isAuthenticated">
        <RouterLink to="/">Главная</RouterLink> |
        <span class="nav-group">
          <strong>Продукты:</strong>
          <RouterLink to="/products2">Продукты 2</RouterLink> |
          <RouterLink to="/product-list">Список товаров</RouterLink> |
          <RouterLink to="/product-form">Создать товар</RouterLink> |
          <RouterLink to="/product-types">Типы товаров</RouterLink> |
          <RouterLink to="/units">Единицы</RouterLink> |
          <RouterLink to="/product-units">Дробные части</RouterLink> |
          <RouterLink to="/ingredients">Ингредиенты</RouterLink>
        </span> |
        <span class="nav-group">
          <strong>Продажи:</strong>
          <RouterLink to="/sales">Продажи</RouterLink> |
          <RouterLink to="/sales/list">Список</RouterLink>
        </span> |
        <span class="nav-group">
          <strong>Цены:</strong>
          <RouterLink to="/prices">Прайсы</RouterLink>
        </span> |
        <span class="nav-group">
          <strong>Партии:</strong>
          <RouterLink to="/lots">Партии</RouterLink>
        </span> |
        <span class="nav-group">
          <strong>QR/Serial:</strong>
          <RouterLink to="/serial/receipts">Приёмка</RouterLink> |
          <RouterLink to="/serial/transfers">Перемещение</RouterLink> |
          <RouterLink to="/serial/inventories">Инвентаризация</RouterLink> |
          <RouterLink to="/serial/scan">Сканер</RouterLink> |
          <RouterLink to="/serial/boxes/manage">Коробки</RouterLink>
        </span> |
        <a href="#" @click="handleLogout">Выйти</a>
      </template>
      <template v-else>
        <RouterLink to="/login">Вход</RouterLink>
      </template>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>

<style scoped>
header {
  line-height: 1.5;
  margin-bottom: 2rem;
}

nav {
  width: 100%;
  font-size: 1rem;
  text-align: left;
  margin-top: 2rem;
}

nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
  border: 0;
}

.nav-group {
  display: inline-block;
}

.nav-group strong {
  color: #64748b;
  font-size: 0.9em;
  margin-right: 0.5rem;
}

.nav-group a {
  border-left: 1px solid var(--color-border);
  padding: 0 0.5rem;
  font-size: 0.95em;
}

.nav-group a:first-of-type {
  border-left: 1px solid var(--color-border);
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 0;
  }
}
</style>
