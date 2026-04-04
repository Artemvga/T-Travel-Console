import axios from "axios";

const AUTH_TOKEN_KEY = "t-travel-auth-token";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_BACKEND_ORIGIN ||
    "",
  timeout: 10000,
});

export function getStoredToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function storeToken(token) {
  if (typeof window === "undefined") {
    return;
  }

  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function clearStoredToken() {
  storeToken("");
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export async function getCarriers() {
  const response = await api.get("/api/carriers/");
  return response.data;
}

export async function getStats() {
  const response = await api.get("/api/stats/");
  return response.data;
}

export async function getGenerationStatus() {
  const response = await api.get("/api/tickets/generation-status/");
  return response.data;
}

export async function getCityDetail(slug) {
  const response = await api.get(`/api/cities/${slug}/`);
  return response.data;
}

export async function searchCities(query) {
  const response = await api.get("/api/cities/search/", {
    params: { q: query },
  });
  return response.data;
}

export async function buildRoute(payload) {
  const response = await api.post("/api/routes/build/", payload);
  return response.data;
}

export async function registerUser(payload) {
  const response = await api.post("/api/auth/register/", payload);
  if (response.data?.token) {
    storeToken(response.data.token);
  }
  return response.data;
}

export async function loginUser(payload) {
  const response = await api.post("/api/auth/login/", payload);
  if (response.data?.token) {
    storeToken(response.data.token);
  }
  return response.data;
}

export async function logoutUser() {
  const response = await api.post("/api/auth/logout/");
  clearStoredToken();
  return response.data;
}

export async function getMe() {
  const response = await api.get("/api/auth/me/");
  return response.data;
}

export async function getFavoriteRoutes() {
  const response = await api.get("/api/routes/favorites/");
  return response.data;
}

export async function saveFavoriteRoute(payload) {
  const response = await api.post("/api/routes/favorites/", payload);
  return response.data;
}

export async function removeFavoriteRoute(id) {
  const response = await api.delete(`/api/routes/favorites/${id}/`);
  return response.data;
}

export function getApiError(error, fallbackMessage) {
  if (!error?.response) {
    return "Ошибка сервера (HTTP 503): сервер временно недоступен.";
  }

  const statusCode = error.response.status || 500;

  if (typeof error?.response?.data === "string") {
    return `Ошибка сервера (HTTP ${statusCode}): ${error.response.data}`;
  }

  if (error?.response?.data?.detail) {
    return `Ошибка сервера (HTTP ${statusCode}): ${error.response.data.detail}`;
  }

  if (error?.response?.data?.message) {
    return `Ошибка сервера (HTTP ${statusCode}): ${error.response.data.message}`;
  }

  if (error?.response?.data && typeof error.response.data === "object") {
    const firstFieldError = Object.values(error.response.data)
      .flat()
      .find(Boolean);
    if (firstFieldError) {
      return `Ошибка сервера (HTTP ${statusCode}): ${firstFieldError}`;
    }
  }

  return `Ошибка сервера (HTTP ${statusCode}): ${fallbackMessage}`;
}
