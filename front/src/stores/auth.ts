import { ref } from 'vue';
import { defineStore } from 'pinia';
import { getToken, getUserPermissions, isAuthenticated as checkIsAuthenticated } from '@/api/authApi';

export const useAuthStore = defineStore('auth', () => {
  const permissions = ref<string[]>([]);
  const isAuthenticated = ref(false);
  const user = ref<any>(null);

  const initializeAuth = () => {
    const token = getToken();
    isAuthenticated.value = checkIsAuthenticated();

    if (isAuthenticated.value && token) {
      // Load permissions from localStorage
      permissions.value = getUserPermissions();
      // Note: we don't have user details here, they would need to be fetched separately
    } else {
      permissions.value = [];
      isAuthenticated.value = false;
      user.value = null;
    }
  };

  const hasPermission = (permission: string): boolean => {
    // Check if user has the specific permission
    // '*' means superuser with all permissions
    if (permissions.value.includes('*')) {
      return true;
    }
    return permissions.value.includes(permission);
  };

  const logout = () => {
    permissions.value = [];
    isAuthenticated.value = false;
    user.value = null;
  };

  return {
    permissions,
    isAuthenticated,
    user,
    initializeAuth,
    hasPermission,
    logout
  };
});