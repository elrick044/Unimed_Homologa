import axios from "axios";
import { clearSession, getRefreshToken, saveSession } from "../auth/session";

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const baseURL = API_URL.endsWith("/api") ? API_URL : `${API_URL.replace(/\/$/, "")}/api`;

export const api = axios.create({
  baseURL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

let refreshRequest = null;

function redirectToLogin() {
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest?._retry) {
      return Promise.reject(error);
    }

    const refresh = getRefreshToken();

    if (!refresh || originalRequest?.url?.includes("/auth/token/refresh/")) {
      clearSession();
      redirectToLogin();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      refreshRequest =
        refreshRequest ||
        axios.post(`${baseURL}/auth/token/refresh/`, {
          refresh,
        });

      const { data } = await refreshRequest;
      refreshRequest = null;

      saveSession({ access: data.access });
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${data.access}`;

      return api(originalRequest);
    } catch (refreshError) {
      refreshRequest = null;
      clearSession();
      redirectToLogin();
      return Promise.reject(refreshError);
    }
  },
);
