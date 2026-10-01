import { listMovements } from "../../api/inventory";
import { UNIT_LABELS } from "../../config/options";
import useFetch from "../../hooks/useFetch";
import { t } from "../../i18n";
import { getErrorMessage } from "../../utils/errors";
import { formatQuantity } from "../../utils/format";
import Alert from "../ui/Alert";
import Modal from "../ui/Modal";
import Spinner from "../ui/Spinner";

const HISTORY_SIZE = 25;

export default function StockHistoryModal({ product, onClose }) {
  const history = useFetch(
    () => listMovements({ product: product.id, page_size: HISTORY_SIZE }),
    product.id
  );
  const movements = history.data?.results ?? [];
  const unit = UNIT_LABELS[product.unit] ?? "";

  return (
    <Modal title={t("history.title", { name: product.name })} onClose={onClose}>
      {history.loading && !history.data && (
        <div role="status" className="flex justify-center py-6 text-brand-700">
          <Spinner className="h-6 w-6" />
        </div>
      )}
      {history.error && (
        <Alert>
          {t("history.loadError")} {getErrorMessage(history.error)}{" "}
          <button type="button" onClick={history.reload} className="font-semibold underline">
            {t("common.tryAgain")}
          </button>
        </Alert>
      )}
      {history.data && movements.length === 0 && (
        <p className="py-4 text-center text-sm text-slate-600">{t("history.empty")}</p>
      )}
      <ul>
        {movements.map((movement) => (
          <li key={movement.id} className="border-b border-slate-200 py-3 last:border-b-0">
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-medium text-slate-900">
                {t(`movement.${movement.movement_type}`)}
              </p>
              <p className="font-semibold text-slate-900">
                {formatQuantity(movement.quantity_change, { signed: true })} {unit}
              </p>
            </div>
            <p className="text-sm text-slate-600">
              {t("history.after", { qty: formatQuantity(movement.stock_after) })}
              {movement.created_by_name &&
                ` · ${t("history.by", { name: movement.created_by_name })}`}
            </p>
            {movement.note && <p className="text-sm text-slate-700">{movement.note}</p>}
            <p className="text-xs text-slate-500">
              {new Date(movement.created_at).toLocaleString()}
            </p>
          </li>
        ))}
      </ul>
      {history.data && history.data.count > HISTORY_SIZE && (
        <p className="mt-3 text-center text-xs text-slate-600">
          {t("history.latest", { count: HISTORY_SIZE })}
        </p>
      )}
    </Modal>
  );
}
