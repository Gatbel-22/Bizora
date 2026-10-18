import customers from "./customers";
import en from "./en";
import expenses from "./expenses";
import inventory from "./inventory";
import sales from "./sales";

const messages = { ...en, ...inventory, ...customers, ...sales, ...expenses };

// t("dashboard.greeting", { name: "Ann" }) -> "Welcome, Ann"
export function t(key, params) {
  const text = messages[key] ?? key;
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
}
