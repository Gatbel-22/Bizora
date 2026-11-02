import { t } from "../../i18n";
import { formatPercent } from "../../utils/format";

export default function StatCard({
  label,
  value,
  hint,
  change,
  compareLabel,
  upIsGood = true,
  estimate = false,
}) {
  const hasChange = change !== null && change !== undefined && change !== 0;
  const up = change > 0;
  const good = up === upIsGood;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="flex items-center gap-2 text-sm text-slate-600">
        {label}
        {estimate && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-900">
            {t("dashboard.estimate")}
          </span>
        )}
      </p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      {hasChange && (
        <p className={`mt-1 text-sm font-medium ${good ? "text-green-800" : "text-red-700"}`}>
          <span aria-hidden="true">{up ? "▲" : "▼"}</span>
          <span className="sr-only">{up ? t("dashboard.up") : t("dashboard.down")}</span>{" "}
          {formatPercent(change)} {t("dashboard.vs", { label: compareLabel })}
        </p>
      )}
      {hint && <p className="mt-1 text-sm text-slate-600">{hint}</p>}
    </div>
  );
}
