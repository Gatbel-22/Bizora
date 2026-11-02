import { Link } from "react-router-dom";
import { UNIT_LABELS } from "../../config/options";
import { t } from "../../i18n";
import { formatQuantity } from "../../utils/format";
import StockBadge from "../ui/StockBadge";

export default function LowStockList({ items }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-600">{t("dashboard.lowStock.allGood")}</p>;
  }

  return (
    <>
      <ul>
        {items.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between gap-3 border-b border-slate-200 py-2 last:border-b-0"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-900">{item.name}</p>
              <p className="text-sm text-slate-600">
                {t("dashboard.lowStock.left", {
                  qty: formatQuantity(item.current_stock),
                  unit: UNIT_LABELS[item.unit] ?? "",
                  min: formatQuantity(item.min_stock_threshold),
                })}
              </p>
            </div>
            <StockBadge status={item.status} />
          </li>
        ))}
      </ul>
      <Link
        to="/products"
        className="mt-2 inline-block text-sm font-semibold text-brand-700 underline"
      >
        {t("dashboard.lowStock.viewAll")}
      </Link>
    </>
  );
}
