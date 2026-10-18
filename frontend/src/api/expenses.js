import api from "./client";
import { cleanParams } from "../utils/params";

const unwrap = (response) => response.data;

export const listExpenses = (params) =>
  api.get("/expenses/", { params: cleanParams(params) }).then(unwrap);
export const getExpenseSummary = (params) =>
  api.get("/expenses/summary/", { params: cleanParams(params) }).then(unwrap);
export const createExpense = (payload) => api.post("/expenses/", payload).then(unwrap);
export const updateExpense = (id, payload) => api.patch(`/expenses/${id}/`, payload).then(unwrap);
export const deleteExpense = (id) => api.delete(`/expenses/${id}/`);

export const listExpenseCategories = (params) =>
  api
    .get("/expense-categories/", { params: cleanParams({ page_size: 100, ...params }) })
    .then(unwrap);
export const createExpenseCategory = (payload) =>
  api.post("/expense-categories/", payload).then(unwrap);
export const updateExpenseCategory = (id, payload) =>
  api.patch(`/expense-categories/${id}/`, payload).then(unwrap);
export const deleteExpenseCategory = (id) => api.delete(`/expense-categories/${id}/`);
