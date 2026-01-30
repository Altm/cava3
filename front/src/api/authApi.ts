import axios from 'axios';

const authApi = axios.create({
  baseURL: '/api/v1/auth'
});

const userApi = axios.create({
  baseURL: '/api/v1'
});

// Request interceptor to add JWT token to requests
userApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Login function
export const login = async (username: string, password: string) => {
  // Using application/x-www-form-urlencoded format for OAuth2
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);

  const response = await authApi.post('/token', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });

  // Store the token in localStorage
  if (response.data.access_token) {
    localStorage.setItem('access_token', response.data.access_token);
  }

  return response.data;
};

// Get current user info
export const getCurrentUser = async () => {
  try {
    const response = await userApi.get('/me');
    return response.data;
  } catch (error) {
    console.error('Error fetching user info:', error);
    throw error;
  }
};

// Logout function
export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_permissions');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!localStorage.getItem('access_token');
};

// Get current token
export const getToken = () => {
  return localStorage.getItem('access_token');
};

// Get user permissions
export const getUserPermissions = (): string[] => {
  const permsStr = localStorage.getItem('user_permissions');
  return permsStr ? JSON.parse(permsStr) : [];
};

// Set user permissions
export const setUserPermissions = (permissions: string[]) => {
  localStorage.setItem('user_permissions', JSON.stringify(permissions));
};