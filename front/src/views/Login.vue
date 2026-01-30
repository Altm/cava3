<template>
  <div class="login-container">
    <div class="login-form">
      <h2>Вход в систему</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">Имя пользователя:</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="Введите имя пользователя"
            required
            class="form-control"
          />
        </div>
        <div class="form-group">
          <label for="password">Пароль:</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Введите пароль"
            required
            class="form-control"
          />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="loading">
          {{ loading ? 'Вход...' : 'Войти' }}
        </button>
        <div v-if="error" class="error-message">{{ error }}</div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { login as authService, getCurrentUser, setUserPermissions } from '@/api/authApi';

const router = useRouter();
const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error.value = 'Пожалуйста, заполните все поля';
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    await authService(username.value, password.value);

    // Get user info and permissions
    const userInfo = await getCurrentUser();
    setUserPermissions(userInfo.permissions);

    // Redirect to home page after successful login
    router.push('/');
  } catch (err: any) {
    console.error('Login error:', err);
    error.value = err.response?.data?.detail || 'Ошибка входа. Проверьте имя пользователя и пароль.';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.login-form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.btn {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  padding: 0.5rem;
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}
</style>