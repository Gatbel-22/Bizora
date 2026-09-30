import api from "./client";

export const registerAccount = (payload) =>
  api.post("/auth/register/", payload).then((response) => response.data);

export const loginRequest = (email, password) =>
  api.post("/auth/login/", { email, password }).then((response) => response.data);

export const logoutRequest = (refresh) => api.post("/auth/logout/", { refresh });

export const fetchMe = () => api.get("/auth/me/").then((response) => response.data);
