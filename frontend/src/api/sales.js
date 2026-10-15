import api from "./client";
import { cleanParams } from "../utils/params";

const unwrap = (response) => response.data;

export const listSales = (params) =>
  api.get("/sales/", { params: cleanParams(params) }).then(unwrap);
export const createSale = (payload) => api.post("/sales/", payload).then(unwrap);
export const cancelSale = (id, reason) => api.post(`/sales/${id}/cancel/`, { reason }).then(unwrap);
export const getReceipt = (id) => api.get(`/sales/${id}/receipt/`).then(unwrap);
