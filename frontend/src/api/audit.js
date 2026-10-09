import api from "./client";
import { cleanParams } from "../utils/params";

export const listAuditLog = (params) =>
  api.get("/audit-log/", { params: cleanParams(params) }).then((response) => response.data);
