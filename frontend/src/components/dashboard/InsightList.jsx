import { Link } from "react-router-dom";
import { t } from "../../i18n";

const STYLES = {
  CRITICAL: "border-red-300 bg-red-50 text-red-950",
  WARNING: "border-amber-300 bg-amber-50 text-amber-950",
  INFO: "border-sky-300 bg-sky-50 text-sky-950",
};

const LINKS = {
  products: "/products",
  customers: "/customers",
  expenses: "/expenses",
  sales: "/sales",
};

export default function InsightList({ insights }) {
  if (insights.length === 0) {
    return <p className="text-sm text-slate-600">{t("dashboard.insights.none")}</p>;
  }

  return (
    <ul className="space-y-2">
      {insights.map((insight, index) => {
        const path = LINKS[insight.related?.type];
        return (
          <li
            key={`${insight.type}-${index}`}
            className={`rounded-lg border px-4 py-3 text-sm ${STYLES[insight.severity] ?? STYLES.INFO}`}
          >
            <p className="font-semibold">
              {t(`dashboard.insight.${insight.severity}`)}: {insight.title}
            </p>
            <p className="mt-0.5">{insight.message}</p>
            {path && (
              <Link to={path} className="mt-1 inline-block min-h-6 font-semibold underline">
                {t("dashboard.insight.view")}
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}
