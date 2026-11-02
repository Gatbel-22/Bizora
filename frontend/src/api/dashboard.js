import api from "./client";
import { cleanParams } from "../utils/params";

export const getDashboard = (params) =>
  api.get("/dashboard/", { params: cleanParams(params) }).then((response) => response.data);

export const getProfit = (params) =>
  api.get("/profit/", { params: cleanParams(params) }).then((response) => response.data);
