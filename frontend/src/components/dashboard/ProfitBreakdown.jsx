import { t } from "../../i18n";
import { formatMoney } from "../../utils/format";

function Row({ label, value, sign, strong, negative, note }) {
  return (
    <div className={`flex justify-between gap-3 py-2 ${strong ? "border-t border-slate-300" : ""}`}>
      <dt className={strong ? "font-semibold text-slate-900" : "text-slate-700"}>
        {sign && <span aria-hidden="true">{sign} </span>}
        {label}
        {note && <span className="block text-xs font-normal text-slate-600">{note}</span>}
      </dt>
      <dd
        className={`${strong ? "font-bold" : "font-medium"} ${negative ? "text-red-700" : "text-slate-900"}`}
      >
        {value}
      </dd>
    </div>
  );
}

export default function ProfitBreakdown({ figures, currency }) {
  const money = (value) => formatMoney(value, currency);
  const margin = figures.gross_margin_percent;

  return (
    <section
      aria-labelledby="breakdown-heading"
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      <h2 id="breakdown-heading" className="mb-2 text-base font-semibold text-slate-900">
        {t("dashboard.breakdown.title")}
      </h2>
      <dl className="text-sm">
        <Row label={t("dashboard.breakdown.revenue")} value={money(figures.revenue)} />
        <Row
          label={t("dashboard.breakdown.cogs")}
          value={money(figures.cost_of_goods_sold)}
          sign="−"
        />
        <Row
          strong
          label={t("dashboard.breakdown.gross")}
          value={money(figures.gross_profit)}
          negative={Number(figures.gross_profit) < 0}
          note={margin !== null ? t("dashboard.margin", { percent: margin }) : undefined}
        />
        <Row
          label={t("dashboard.breakdown.operating")}
          value={money(figures.operating_expenses)}
          sign="−"
        />
        <Row
          strong
          label={t("dashboard.breakdown.net")}
          value={money(figures.estimated_net_profit)}
          negative={Number(figures.estimated_net_profit) < 0}
        />
      </dl>

      {Number(figures.credit_sales) > 0 && (
        <p className="mt-3 text-sm text-slate-700">
          {t("dashboard.breakdown.credit", { amount: money(figures.credit_sales) })}
        </p>
      )}
      {Number(figures.other_spending) > 0 && (
        <p className="mt-1 text-sm text-slate-700">
          {t("dashboard.notCounted", { amount: money(figures.other_spending) })}
        </p>
      )}
      <p className="mt-3 text-xs text-slate-600">{t("dashboard.breakdown.disclaimer")}</p>
    </section>
  );
}
