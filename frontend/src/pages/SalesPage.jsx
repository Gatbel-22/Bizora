import { useState } from "react";
import { Link } from "react-router-dom";
import { listSales } from "../api/sales";
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

const NEW_SALE_LINK =
  "inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900";

export default function SalesPage() {
  const { business } = useAuth();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [hasBalance, setHasBalance] = useState(false);
  const [page, setPage] = useState(1);

  const debouncedSearch = useDebounce(search.trim());
  const params = {
    search: debouncedSearch,
    status,
    has_balance: hasBalance ? true : undefined,
    page,
    page_size: PAGE_SIZE,
  };
  const sales = useFetch(() => listSales(params), JSON.stringify(params));

  const rows = sales.data?.results ?? [];
  const pageCount = Math.ceil((sales.data?.count ?? 0) / PAGE_SIZE);
  const hasFilters = Boolean(debouncedSearch || status || hasBalance);
  const firstLoad = sales.loading && !sales.data;
  const isEmpty = !sales.loading && !sales.error && rows.length === 0;

  const statusOptions = [
    { value: "", label: t("sales.filter.allStatuses") },
    { value: "COMPLETED", label: t("sales.filter.completed") },
    { value: "CANCELLED", label: t("sales.filter.cancelled") },
  ];

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t("sales.title")}</h1>
          <p className="mt-1 text-slate-600">{t("sales.subtitle")}</p>
        </div>
        <Link to="/sales/new" className={NEW_SALE_LINK}>
          {t("sales.new")}
        </Link>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr]">
        <TextField
          label={t("sales.searchLabel")}
          type="search"
          placeholder={t("sales.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <SelectField
          label={t("sales.filter.status")}
          options={statusOptions}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
        />
        <label className="flex min-h-11 items-center gap-3 self-end text-sm font-medium text-slate-800">
          <input
            type="checkbox"
            checked={hasBalance}
            onChange={(event) => {
              setHasBalance(event.target.checked);
              setPage(1);
            }}
            className="h-5 w-5"
          />
          {t("sales.filter.hasBalance")}
        </label>
      </div>

      {sales.error && (
        <Alert className="mb-4">
          {t("sales.loadError")} {getErrorMessage(sales.error)}{" "}
          <button type="button" onClick={sales.reload} className="font-semibold underline">
            {t("common.tryAgain")}
          </button>
        </Alert>
      )}

      {firstLoad && (
        <div role="status" className="flex justify-center py-16 text-brand-700">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {isEmpty && (
        <EmptyState
          title={hasFilters ? t("sales.emptySearch.title") : t("sales.empty.title")}
          message={hasFilters ? t("sales.emptySearch.message") : t("sales.empty.message")}
        >
          {!hasFilters && (
            <Link to="/sales/new" className={NEW_SALE_LINK}>
              {t("sales.new")}
            </Link>
          )}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={sales.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              sales.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((sale) => {
              const cancelled = sale.status === "CANCELLED";
              const owed = Number(sale.outstanding_amount) > 0;
              return (
                <li key={sale.id} className="border-b border-slate-200 last:border-b-0">
                  <Link
                    to={`/sales/${sale.id}`}
                    className="grid gap-1 p-4 hover:bg-slate-50 sm:grid-cols-[1fr_auto] sm:items-center"
                  >
                    <span>
                      <span className="block font-semibold text-slate-900">
                        {sale.number}
                        {cancelled && (
                          <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-900">
                            {t("sales.status.CANCELLED")}
                          </span>
                        )}
                      </span>
                      <span className="block text-sm text-slate-600">
                        {formatDateTime(sale.sold_at)} · {sale.customer_name ?? t("sales.walkIn")}
                      </span>
                    </span>
                    <span className="sm:text-right">
                      <span
                        className={`block font-semibold ${
                          cancelled ? "text-slate-500 line-through" : "text-slate-900"
                        }`}
                      >
                        {formatMoney(sale.total, business.currency)}
                      </span>
                      {!cancelled && (
                        <span
                          className={`block text-sm ${
                            owed ? "font-medium text-red-700" : "text-slate-600"
                          }`}
                        >
                          {owed
                            ? t("sales.balanceOwed", {
                                amount: formatMoney(sale.outstanding_amount, business.currency),
                              })
                            : t("sales.paidInFull")}
                        </span>
                      )}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            disabled={sales.loading}
          />
        </>
      )}
    </>
  );
}
