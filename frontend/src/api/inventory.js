import api from "./client";
import { cleanParams } from "../utils/params";

const unwrap = (response) => response.data;

export const listProducts = (params) =>
  api.get("/products/", { params: cleanParams(params) }).then(unwrap);
export const createProduct = (payload) => api.post("/products/", payload).then(unwrap);
export const updateProduct = (id, payload) => api.patch(`/products/${id}/`, payload).then(unwrap);
export const adjustStock = (id, payload) =>
  api.post(`/products/${id}/stock/`, payload).then(unwrap);

export const listCategories = (params) =>
  api.get("/categories/", { params: cleanParams({ page_size: 100, ...params }) }).then(unwrap);
export const createCategory = (payload) => api.post("/categories/", payload).then(unwrap);
export const deleteCategory = (id) => api.delete(`/categories/${id}/`);

export const listMovements = (params) =>
  api.get("/inventory/movements/", { params: cleanParams(params) }).then(unwrap);
