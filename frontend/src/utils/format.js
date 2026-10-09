export function formatMoney(value, currency = "SSP") {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      currencyDisplay: "code",
      minimumFractionDigits: Number.isInteger(number) ? 0 : 2,
      maximumFractionDigits: 2,
    }).format(number);
  } catch {
    return `${currency} ${number.toLocaleString()}`;
  }
}

export function formatQuantity(value, { signed = false } = {}) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number.toLocaleString(undefined, {
    maximumFractionDigits: 3,
    ...(signed ? { signDisplay: "exceptZero" } : {}),
  });
}

// For plain dates from the API ("2026-10-07").
export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

export function formatDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
}

// Today's date in the user's own timezone, as YYYY-MM-DD (for date inputs).
export function todayISO() {
  return new Date().toLocaleDateString("en-CA");
}
