import { Trash2 } from "lucide-react";
import { t } from "../../i18n";
import { exceedsStock, isLineValid, lineTotal } from "../../utils/cart";
import { formatMoney, formatQuantity } from "../../utils/format";

const STEP_BUTTON =
  "flex h-11 w-11 items-center justify-center rounded-lg border border-slate-300 bg-white text-xl font-semibold text-slate-800 hover:bg-slate-50";

export default function CartLine({ line, currency, onQuantityChange, onStep, onRemove }) {
  const invalid = !isLineValid(line);

  return (
    <li className="border-b border-slate-200 p-3 last:border-b-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-slate-900">{line.name}</p>
          <p className="text-sm text-slate-600">
            {t("newSale.each", { price: formatMoney(line.unitPrice, currency) })}
          </p>
        </div>
        <p className="font-semibold text-slate-900">{formatMoney(lineTotal(line), currency)}</p>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <button
          type="button"
          aria-label={t("newSale.decrease")}
          onClick={() => onStep(line.productId, -1)}
          className={STEP_BUTTON}
        >
          −
        </button>
        <input
          aria-label={t("newSale.quantity")}
          aria-invalid={invalid ? "true" : undefined}
          inputMode="decimal"
          value={line.quantity}
          onChange={(event) => onQuantityChange(line.productId, event.target.value)}
          className={`h-11 w-20 rounded-lg border bg-white px-2 text-center text-base text-slate-900 ${
            invalid ? "border-red-600" : "border-slate-300"
          }`}
        />
        <button
          type="button"
          aria-label={t("newSale.increase")}
          onClick={() => onStep(line.productId, 1)}
          className={STEP_BUTTON}
        >
          +
        </button>
        <button
          type="button"
          aria-label={`${t("newSale.remove")}: ${line.name}`}
          onClick={() => onRemove(line.productId)}
          className="ml-auto flex h-11 w-11 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"
        >
          <Trash2 className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      {invalid && (
        <p className="mt-1 text-sm font-medium text-red-700">{t("newSale.invalidQuantity")}</p>
      )}
      {exceedsStock(line) && (
        <p className="mt-1 text-sm font-medium text-amber-800">
          {t("newSale.onlyInStock", { qty: formatQuantity(line.stock) })}
        </p>
      )}
    </li>
  );
}
