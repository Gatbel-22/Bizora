import { UNIT_LABELS } from "../../config/options";
import { t } from "../../i18n";
import { formatMoney, formatQuantity } from "../../utils/format";
import Button from "../ui/Button";
import StockBadge from "../ui/StockBadge";

export default function ProductRow({ product, currency, canManage, onEdit, onAdjust, onHistory }) {
  const details = [product.sku, product.category_name].filter(Boolean).join(" · ");

  return (
    <li className="grid gap-3 border-b border-slate-200 p-4 last:border-b-0 md:grid-cols-[minmax(0,2fr)_1fr_1.2fr_auto] md:items-center">
      <div className="min-w-0">
        <p className="font-semibold text-slate-900">
          {product.name}
          {!product.is_active && (
            <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-800">
              {t("products.inactive")}
            </span>
          )}
        </p>
        {details && <p className="truncate text-sm text-slate-600">{details}</p>}
      </div>

      <div className="text-sm">
        <p className="font-semibold text-slate-900">
          {formatMoney(product.selling_price, currency)}
        </p>
        {product.purchase_price !== undefined && (
          <p className="text-slate-600">
            {t("products.cost")} {formatMoney(product.purchase_price, currency)}
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm md:block md:space-y-1">
        <p className="font-semibold text-slate-900">
          {formatQuantity(product.current_stock)}{" "}
          <span className="font-normal text-slate-600">{UNIT_LABELS[product.unit]}</span>
        </p>
        <StockBadge status={product.stock_status} />
      </div>

      {canManage && (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => onAdjust(product)}
            aria-label={`${t("products.adjust")}: ${product.name}`}
          >
            {t("products.adjust")}
          </Button>
          <Button
            variant="ghost"
            onClick={() => onHistory(product)}
            aria-label={`${t("products.history")}: ${product.name}`}
          >
            {t("products.history")}
          </Button>
          <Button
            variant="ghost"
            onClick={() => onEdit(product)}
            aria-label={`${t("products.edit")}: ${product.name}`}
          >
            {t("products.edit")}
          </Button>
        </div>
      )}
    </li>
  );
}
