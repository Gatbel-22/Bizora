import axios from "axios";
import { tokenStorage } from "../utils/tokenStorage";

const baseURL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// These endpoints must never trigger the refresh-and-retry flow.
const NO_REFRESH_PATHS = ["/auth/login/", "/auth/register/", "/auth/refresh/", "/auth/logout/"];

let authFailureHandler = () => {};
export function setAuthFailureHandler(handler) {
  authFailureHandler = handler;
}

let refreshPromise = null;

async function refreshAccessToken() {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) throw new Error("No refresh token available");
  // Plain axios (not `api`) so this call skips our interceptors and can't loop.
  const { data } = await axios.post(`${baseURL}/auth/refresh/`, { refresh }, { timeout: 15000 });
  tokenStorage.setTokens({ access: data.access, refresh: data.refresh ?? refresh });
  return data.access;
}

api.interceptors.request.use((config) => {
  const access = tokenStorage.getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  const businessId = tokenStorage.getBusinessId();
  if (businessId) config.headers["X-Business-ID"] = businessId;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const unauthorized = error.response?.status === 401;
    const skip =
      !original ||
      original._retried ||
      NO_REFRESH_PATHS.some((path) => original.url?.includes(path));

    if (!unauthorized || skip) return Promise.reject(error);
    original._retried = true;

    let access;
    try {
      // Several requests can fail at once; they all share one refresh call.
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      access = await refreshPromise;
    } catch (refreshError) {
      const rejectedByServer = Boolean(refreshError.response);
      const noToken = refreshError.message === "No refresh token available";
      if (rejectedByServer || noToken) {
        tokenStorage.clear();
        authFailureHandler();
      }
      return Promise.reject(error);
    }

    original.headers.Authorization = `Bearer ${access}`;
    return api(original);
  }
);

export default api;
