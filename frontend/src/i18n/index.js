import en from "./en";

const messages = en;

// t("dashboard.greeting", { name: "Ann" }) -> "Welcome, Ann"
export function t(key, params) {
  const text = messages[key] ?? key;
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
}
