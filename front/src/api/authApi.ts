import axios from 'axios';

const authApi = axios.create({
  baseURL: '/api/v1/auth'
});

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

// Logout function
export const logout = () => {
  localStorage.removeItem('access_token');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!localStorage.getItem('access_token');
};

// Get current token
export const getToken = () => {
  return localStorage.getItem('access_token');
};