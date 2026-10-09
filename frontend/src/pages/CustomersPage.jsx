import { useState } from "react";
import { Link } from "react-router-dom";
import { listCustomers } from "../api/customers";
import CustomerFormModal from "../components/customers/CustomerFormModal";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import SelectField from "../components/ui/SelectField";
import Spinner from "../components/ui/Spinner";
import TextField from "../components/ui/TextField";
import { PAGE_SIZE } from "../config/pagination";
import { ROLES } from "../config/roles";
import useAuth from "../hooks/useAuth";
import useDebounce from "../hooks/useDebounce";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { formatMoney } from "../utils/format";

export default function CustomersPage() {
  const { role, business } = useAuth();
  const canEdit = role !== ROLES.STAFF;

  const [search, setSearch] = useState("");
  const [balanceFilter, setBalanceFilter] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState("");

  const debouncedSearch = useDebounce(search.trim());
  const params = {
    search: debouncedSearch,
    has_balance: balanceFilter === "owing" ? true : undefined,
    overdue: balanceFilter === "overdue" ? true : undefined,
    is_active: showInactive ? undefined : true,
    page,
    page_size: PAGE_SIZE,
  };
  const customers = useFetch(() => listCustomers(params), JSON.stringify(params));

  const rows = customers.data?.results ?? [];
  const pageCount = Math.ceil((customers.data?.count ?? 0) / PAGE_SIZE);
  const hasFilters = Boolean(debouncedSearch || balanceFilter || showInactive);
  const firstLoad = customers.loading && !customers.data;
  const isEmpty = !customers.loading && !customers.error && rows.length === 0;

  const balanceOptions = [
    { value: "", label: t("customers.filter.all") },
    { value: "owing", label: t("customers.filter.owing") },
    { value: "overdue", label: t("customers.filter.overdue") },
  ];

  const handleSaved = (message) => {
    setModal(null);
    setNotice(message);
    customers.reload();
  };

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {t("customers.title")}
          </h1>
          <p className="mt-1 text-slate-600">{t("customers.subtitle")}</p>
        </div>
        <Button onClick={() => setModal({ customer: null })}>{t("customers.add")}</Button>
      </div>

      {notice && (
        <Alert variant="success" className="mb-4">
          {notice}
        </Alert>
      )}

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr]">
        <TextField
          label={t("customers.searchLabel")}
          type="search"
          placeholder={t("customers.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
            setNotice("");
          }}
        />
        <SelectField
          label={t("customers.filter.balance")}
          options={balanceOptions}
          value={balanceFilter}
          onChange={(event) => {
            setBalanceFilter(event.target.value);
            setPage(1);
            setNotice("");
          }}
        />
        <label className="flex min-h-11 items-center gap-3 self-end text-sm font-medium text-slate-800">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(event) => {
              setShowInactive(event.target.checked);
              setPage(1);
            }}
            className="h-5 w-5"
          />
          {t("customers.filter.showInactive")}
        </label>
      </div>

      {customers.error && (
        <Alert className="mb-4">
          {t("customers.loadError")} {getErrorMessage(customers.error)}{" "}
          <button type="button" onClick={customers.reload} className="font-semibold underline">
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
          title={hasFilters ? t("customers.emptySearch.title") : t("customers.empty.title")}
          message={hasFilters ? t("customers.emptySearch.message") : t("customers.empty.message")}
        >
          {!hasFilters && (
            <Button onClick={() => setModal({ customer: null })}>{t("customers.add")}</Button>
          )}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={customers.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              customers.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((customer) => {
              const owes = Number(customer.outstanding_balance) > 0;
              const overdue = Number(customer.overdue_balance) > 0;
              const contact = [customer.phone, customer.email].filter(Boolean).join(" · ");
              return (
                <li
                  key={customer.id}
                  className="grid gap-3 border-b border-slate-200 p-4 last:border-b-0 md:grid-cols-[minmax(0,2fr)_1.5fr_auto] md:items-center"
                >
                  <div className="min-w-0">
                    <Link
                      to={`/customers/${customer.id}`}
                      className="font-semibold text-slate-900 underline-offset-2 hover:underline"
                    >
                      {customer.name}
                    </Link>
                    {!customer.is_active && (
                      <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-800">
                        {t("customers.inactive")}
                      </span>
                    )}
                    {contact && <p className="truncate text-sm text-slate-600">{contact}</p>}
                  </div>
                  <div className="text-sm">
                    {owes ? (
                      <>
                        <p className="font-semibold text-slate-900">
                          {t("customers.owes", {
                            amount: formatMoney(customer.outstanding_balance, business.currency),
                          })}
                        </p>
                        {overdue && (
                          <p className="font-medium text-red-700">
                            {t("customers.overdueAmount", {
                              amount: formatMoney(customer.overdue_balance, business.currency),
                            })}
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-slate-600">{t("customers.noBalance")}</p>
                    )}
                  </div>
                  {canEdit && (
                    <Button
                      variant="ghost"
                      onClick={() => setModal({ customer })}
                      aria-label={`${t("customers.edit")}: ${customer.name}`}
                    >
                      {t("customers.edit")}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            disabled={customers.loading}
          />
        </>
      )}

      {modal && (
        <CustomerFormModal
          customer={modal.customer}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
