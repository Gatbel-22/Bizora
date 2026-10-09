import api from "./client";
import { cleanParams } from "../utils/params";

const unwrap = (response) => response.data;

export const listCustomers = (params) =>
  api.get("/customers/", { params: cleanParams(params) }).then(unwrap);
export const getCustomer = (id) => api.get(`/customers/${id}/`).then(unwrap);
export const createCustomer = (payload) => api.post("/customers/", payload).then(unwrap);
export const updateCustomer = (id, payload) => api.patch(`/customers/${id}/`, payload).then(unwrap);

export const listReceivables = (params) =>
  api.get("/receivables/", { params: cleanParams(params) }).then(unwrap);
export const createReceivable = (payload) => api.post("/receivables/", payload).then(unwrap);

export const listCustomerPayments = (params) =>
  api.get("/customer-payments/", { params: cleanParams(params) }).then(unwrap);
export const recordCustomerPayment = (payload) =>
  api.post("/customer-payments/", payload).then(unwrap);
