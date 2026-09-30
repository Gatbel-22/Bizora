// Tokens live in localStorage so a session survives page reloads. Trade-off: any
// script running on the page could read them, so we keep the frontend free of
// third-party scripts and rely on short-lived access tokens (30 min).
const ACCESS = "bizora.access";
const REFRESH = "bizora.refresh";
const BUSINESS = "bizora.businessId";

function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {
    // Storage unavailable (private mode, quota). The session just won't persist.
  }
}

export const tokenStorage = {
  getAccess: () => read(ACCESS),
  getRefresh: () => read(REFRESH),
  getBusinessId: () => read(BUSINESS),
  hasSession: () => Boolean(read(ACCESS) || read(REFRESH)),
  setTokens({ access, refresh }) {
    write(ACCESS, access);
    write(REFRESH, refresh);
  },
  setBusinessId: (id) => write(BUSINESS, id),
  clear() {
    write(ACCESS, null);
    write(REFRESH, null);
    write(BUSINESS, null);
  },
};
