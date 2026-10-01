import { t } from "../../i18n";

const STYLES = {
  in_stock: "bg-green-100 text-green-900",
  low: "bg-amber-100 text-amber-900",
  out: "bg-red-100 text-red-900",
};

export default function StockBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        STYLES[status] ?? "bg-slate-100 text-slate-800"
      }`}
    >
      {t(`products.status.${status}`)}
    </span>
  );
}
