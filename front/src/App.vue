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
        <RouterLink to="/product-list">Список товаров</RouterLink> |
        <RouterLink to="/product-form">Создать товар</RouterLink> |
        <RouterLink to="/product-types">Типы товаров</RouterLink> |
        <RouterLink to="/sales">Продажи</RouterLink> |
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
