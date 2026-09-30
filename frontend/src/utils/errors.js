import { t } from "../i18n";

function apiError(error) {
  return error?.response?.data?.error ?? null;
}

// One friendly sentence for a whole-form error banner.
export function getErrorMessage(error) {
  if (error?.code === "ECONNABORTED") return t("error.timeout");
  if (!error?.response) return t("error.network");

  const { status } = error.response;
  const api = apiError(error);

  if (status >= 500) return t("error.server");
  if (status === 429) return t("error.throttled");

  const nonField = api?.details?.non_field_errors;
  if (nonField) return [].concat(nonField).join(" ");

  return api?.message ?? t("error.generic");
}

// Per-field messages from a 400 response: { email: "This email is already registered." }
export function getFieldErrors(error) {
  const details = apiError(error)?.details;
  if (!details || typeof details !== "object") return {};

  const result = {};
  for (const [field, value] of Object.entries(details)) {
    if (field === "non_field_errors") continue;
    if (Array.isArray(value)) result[field] = value.join(" ");
    else if (typeof value === "string") result[field] = value;
  }
  return result;
}
