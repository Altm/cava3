<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav>
      <RouterLink to="/">Home</RouterLink>
      <RouterLink to="/product-form">Product Form</RouterLink>
    </nav>
  </header>
  
  <main>
    <RouterView />
  </main>
</template>

<style scoped>
header {
  line-height: 1.5;
  border-bottom: 1px solid #eaeaea;
  padding: 0 1rem;
}

nav {
  display: flex;
  gap: 1rem;
  padding: 1rem 0;
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
  border-left: 1px solid #eaeaea;
  font-weight: 600;
}

nav a:first-of-type {
  border: 0;
}
</style>
