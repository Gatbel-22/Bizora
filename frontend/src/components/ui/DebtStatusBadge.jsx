import { t } from "../../i18n";

const STYLES = {
  current: "bg-slate-100 text-slate-800",
  due_soon: "bg-amber-100 text-amber-900",
  overdue: "bg-red-100 text-red-900",
  paid: "bg-green-100 text-green-900",
};

export default function DebtStatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        STYLES[status] ?? STYLES.current
      }`}
    >
      {t(`debt.status.${status}`)}
    </span>
  );
}
