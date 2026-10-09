import { useState } from "react";
import { listAuditLog } from "../api/audit";
import Alert from "../components/ui/Alert";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import SelectField from "../components/ui/SelectField";
import Spinner from "../components/ui/Spinner";
import TextField from "../components/ui/TextField";
import { PAGE_SIZE } from "../config/pagination";
import useAuth from "../hooks/useAuth";
import useDebounce from "../hooks/useDebounce";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { formatDateTime, formatMoney } from "../utils/format";

const TYPES = ["product", "category", "supplier", "customer", "receivable", "customerpayment"];

const prettyField = (name) => name.replace(/_/g, " ");

const showValue = (value) => {
  if (value === null || value === undefined || value === "") return t("activity.empty.value");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
};

// Turns one audit entry into short readable lines.
function describe(entry, currency) {
  const lines = Object.entries(entry.changes ?? {})
    .slice(0, 6)
    .map(
      ([field, { old, new: next }]) =>
        `${prettyField(field)}: ${showValue(old)} → ${showValue(next)}`
    );

  const meta = entry.metadata ?? {};
  if (entry.action === "product.stock_adjusted") {
    lines.push(`Stock: ${Number(meta.stock_before)} → ${Number(meta.stock_after)}`);
    if (meta.note) lines.push(meta.note);
  } else if (entry.action === "payment.recorded") {
    lines.push(`${formatMoney(meta.amount, currency)} · ${t(`method.${meta.method}`)}`);
  } else if (entry.action === "receivable.created") {
    lines.push(formatMoney(meta.amount, currency));
  }
  return lines;
}

export default function ActivityPage() {
  const { business } = useAuth();
  const [search, setSearch] = useState("");
  const [objectType, setObjectType] = useState("");
  const [page, setPage] = useState(1);

  const debouncedSearch = useDebounce(search.trim());
  const params = {
    search: debouncedSearch,
    object_type: objectType,
    page,
    page_size: PAGE_SIZE,
  };
  const log = useFetch(() => listAuditLog(params), JSON.stringify(params));

  const rows = log.data?.results ?? [];
  const pageCount = Math.ceil((log.data?.count ?? 0) / PAGE_SIZE);
  const typeOptions = [
    { value: "", label: t("activity.filter.allTypes") },
    ...TYPES.map((type) => ({ value: type, label: t(`activity.type.${type}`) })),
  ];

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t("activity.title")}</h1>
        <p className="mt-1 text-slate-600">{t("activity.subtitle")}</p>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-[2fr_1fr]">
        <TextField
          label={t("activity.searchLabel")}
          type="search"
          placeholder={t("activity.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <SelectField
          label={t("activity.filter.type")}
          options={typeOptions}
          value={objectType}
          onChange={(event) => {
            setObjectType(event.target.value);
            setPage(1);
          }}
        />
      </div>

      {log.error && (
        <Alert className="mb-4">
          {t("activity.loadError")} {getErrorMessage(log.error)}{" "}
          <button type="button" onClick={log.reload} className="font-semibold underline">
            {t("common.tryAgain")}
          </button>
        </Alert>
      )}

      {log.loading && !log.data && (
        <div role="status" className="flex justify-center py-16 text-brand-700">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {log.data && rows.length === 0 && !log.loading && (
        <EmptyState title={t("activity.empty.title")} message={t("activity.empty.message")} />
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={log.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              log.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((entry) => (
              <li key={entry.id} className="border-b border-slate-200 p-4 last:border-b-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium text-slate-900">
                    {t(`activity.action.${entry.action}`)}
                    {entry.object_label && (
                      <span className="font-semibold">: {entry.object_label}</span>
                    )}
                  </p>
                  <p className="text-xs text-slate-500">{formatDateTime(entry.created_at)}</p>
                </div>
                <p className="text-sm text-slate-600">
                  {t("history.by", { name: entry.actor_name })}
                </p>
                {describe(entry, business.currency).map((line, index) => (
                  <p key={index} className="text-sm text-slate-700">
                    {line}
                  </p>
                ))}
              </li>
            ))}
          </ul>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            disabled={log.loading}
          />
        </>
      )}
    </>
  );
}
