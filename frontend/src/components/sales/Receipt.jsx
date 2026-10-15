import { t } from "../../i18n";
import { formatDateTime, formatMoney, formatQuantity } from "../../utils/format";

export default function Receipt({ receipt }) {
  const money = (value) => formatMoney(value, receipt.business.currency);
  const cancelled = receipt.status === "CANCELLED";

  return (
    <article className="mx-auto w-full max-w-sm rounded-xl border border-slate-200 bg-white p-5 text-sm shadow-sm print:border-0 print:shadow-none">
      <header className="text-center">
        <h2 className="text-lg font-bold text-slate-900">{receipt.business.name}</h2>
        {receipt.business.address && <p className="text-slate-600">{receipt.business.address}</p>}
        {receipt.business.phone && <p className="text-slate-600">{receipt.business.phone}</p>}
      </header>

      {cancelled && (
        <div
          role="alert"
          className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-red-900"
        >
          <p className="font-semibold">{t("receipt.cancelled")}</p>
          {receipt.cancel_reason && (
            <p>{t("receipt.cancelledReason", { reason: receipt.cancel_reason })}</p>
          )}
        </div>
      )}

      <div className="mt-4 border-t border-dashed border-slate-300 pt-3 text-slate-700">
        <p className="font-semibold text-slate-900">
          {t("receipt.number", { number: receipt.number })}
        </p>
        <p>{formatDateTime(receipt.sold_at)}</p>
        {receipt.served_by && <p>{t("receipt.servedBy", { name: receipt.served_by })}</p>}
        {receipt.customer && <p>{t("receipt.customer", { name: receipt.customer })}</p>}
      </div>

      <ul className="mt-3 border-t border-dashed border-slate-300 pt-3">
        {receipt.items.map((item, index) => (
          <li key={index} className="flex justify-between gap-3 py-1">
            <span className="min-w-0">
              <span className="block font-medium text-slate-900">{item.name}</span>
              <span className="block text-slate-600">
                {formatQuantity(item.quantity)} × {money(item.unit_price)}
              </span>
            </span>
            <span className="font-medium text-slate-900">{money(item.line_total)}</span>
          </li>
        ))}
      </ul>

      <dl className="mt-3 space-y-1 border-t border-dashed border-slate-300 pt-3">
        {Number(receipt.discount) > 0 && (
          <>
            <div className="flex justify-between">
              <dt className="text-slate-700">{t("receipt.subtotal")}</dt>
              <dd>{money(receipt.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-700">{t("receipt.discount")}</dt>
              <dd>-{money(receipt.discount)}</dd>
            </div>
          </>
        )}
        <div className="flex justify-between text-base">
          <dt className="font-semibold text-slate-900">{t("receipt.total")}</dt>
          <dd className="font-bold text-slate-900">{money(receipt.total)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-700">{t("receipt.paid")}</dt>
          <dd>{money(receipt.amount_paid)}</dd>
        </div>
        {Number(receipt.outstanding_amount) > 0 && (
          <div className="flex justify-between font-semibold text-red-700">
            <dt>{t("receipt.balance")}</dt>
            <dd>{money(receipt.outstanding_amount)}</dd>
          </div>
        )}
      </dl>

      {receipt.note && <p className="mt-3 text-slate-700">{receipt.note}</p>}
      <p className="mt-4 text-center text-slate-600">{t("receipt.thanks")}</p>
    </article>
  );
}
