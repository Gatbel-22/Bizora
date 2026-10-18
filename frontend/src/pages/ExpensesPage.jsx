import { useState } from "react";
import {
  deleteExpense,
  getExpenseSummary,
  listExpenseCategories,
  listExpenses,
} from "../api/expenses";
import { listSuppliers } from "../api/inventory";
import ExpenseCategoriesModal from "../components/expenses/ExpenseCategoriesModal";
import ExpenseFormModal from "../components/expenses/ExpenseFormModal";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import SelectField from "../components/ui/SelectField";
import Spinner from "../components/ui/Spinner";
import TextField from "../components/ui/TextField";
import { PAYMENT_METHODS } from "../config/options";
import { PAGE_SIZE } from "../config/pagination";
import { ROLES } from "../config/roles";
import useAuth from "../hooks/useAuth";
import useDebounce from "../hooks/useDebounce";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { formatDate, formatMoney } from "../utils/format";

export default function ExpensesPage() {
  const { role, business } = useAuth();
  const canDelete = role === ROLES.OWNER;
  const currency = business.currency;

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [method, setMethod] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState("");
  const [deleteId, setDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const debouncedSearch = useDebounce(search.trim());
  const filters = {
    search: debouncedSearch,
    category,
    payment_method: method,
    date_from: dateFrom,
    date_to: dateTo,
  };
  const listParams = { ...filters, page, page_size: PAGE_SIZE };

  const expenses = useFetch(() => listExpenses(listParams), JSON.stringify(listParams));
  const summary = useFetch(() => getExpenseSummary(filters), JSON.stringify(filters));
  const categories = useFetch(() => listExpenseCategories(), "expense-categories");
  const suppliers = useFetch(() => listSuppliers(), "suppliers");

  const rows = expenses.data?.results ?? [];
  const pageCount = Math.ceil((expenses.data?.count ?? 0) / PAGE_SIZE);
  const hasFilters = Boolean(debouncedSearch || category || method || dateFrom || dateTo);
  const firstLoad = expenses.loading && !expenses.data;
  const isEmpty = !expenses.loading && !expenses.error && rows.length === 0;
  const money = (value) => formatMoney(value, currency);

  const reloadAll = () => {
    expenses.reload();
    summary.reload();
  };

  const handleSaved = (message) => {
    setModal(null);
    setNotice(message);
    reloadAll();
  };

  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
    setNotice("");
  };

  const clearFilters = () => {
    setSearch("");
    setCategory("");
    setMethod("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const handleDelete = async (expense) => {
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteExpense(expense.id);
      setDeleteId(null);
      setNotice(t("expenses.deleted"));
      reloadAll();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setDeleteId(null);
    } finally {
      setDeleting(false);
    }
  };

  const categoryOptions = [
    { value: "", label: t("expenses.filter.allCategories") },
    ...(categories.data?.results ?? []).map((item) => ({ value: item.id, label: item.name })),
  ];
  const methodOptions = [
    { value: "", label: t("expenses.filter.allMethods") },
    ...PAYMENT_METHODS.map((value) => ({ value, label: t(`method.${value}`) })),
  ];

  const totalNumber = Number(summary.data?.total ?? 0);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {t("expenses.title")}
          </h1>
          <p className="mt-1 text-slate-600">{t("expenses.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setModal({ type: "categories" })}>
            {t("expenses.categories")}
          </Button>
          <Button onClick={() => setModal({ type: "form", expense: null })}>
            {t("expenses.add")}
          </Button>
        </div>
      </div>

      {notice && (
        <Alert variant="success" className="mb-4">
          {notice}
        </Alert>
      )}
      {deleteError && <Alert className="mb-4">{deleteError}</Alert>}

      <section
        aria-label={t("expenses.total")}
        className="mb-6 rounded-xl border border-slate-200 bg-white p-4"
      >
        <p className="text-sm text-slate-600">{t("expenses.total")}</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">
          {summary.data ? money(summary.data.total) : "-"}
        </p>
        {summary.data && (
          <p className="text-sm text-slate-600">
            {t("expenses.count", { count: summary.data.count })}
          </p>
        )}
        {summary.data && summary.data.by_category.length > 0 && (
          <div className="mt-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-800">
              {t("expenses.byCategory")}
            </h2>
            <ul className="space-y-2">
              {summary.data.by_category.slice(0, 5).map((item) => (
                <li key={item.category}>
                  <div className="flex justify-between gap-3 text-sm">
                    <span className="text-slate-800">{item.name}</span>
                    <span className="font-medium text-slate-900">{money(item.total)}</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100" aria-hidden="true">
                    <div
                      className="h-2 rounded-full bg-brand-600"
                      style={{
                        width: `${totalNumber > 0 ? (Number(item.total) / totalNumber) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
        {summary.error && (
          <p className="mt-2 text-sm text-red-700">{getErrorMessage(summary.error)}</p>
        )}
      </section>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <TextField
          label={t("expenses.searchLabel")}
          type="search"
          placeholder={t("expenses.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
            setNotice("");
          }}
        />
        <SelectField
          label={t("expenses.filter.category")}
          options={categoryOptions}
          value={category}
          onChange={changeFilter(setCategory)}
        />
        <SelectField
          label={t("expenses.filter.method")}
          options={methodOptions}
          value={method}
          onChange={changeFilter(setMethod)}
        />
        <TextField
          label={t("expenses.filter.from")}
          type="date"
          value={dateFrom}
          onChange={changeFilter(setDateFrom)}
        />
        <TextField
          label={t("expenses.filter.to")}
          type="date"
          value={dateTo}
          onChange={changeFilter(setDateTo)}
        />
        {hasFilters && (
          <Button variant="ghost" onClick={clearFilters} className="self-end">
            {t("expenses.filter.clear")}
          </Button>
        )}
      </div>

      {expenses.error && (
        <Alert className="mb-4">
          {t("expenses.loadError")} {getErrorMessage(expenses.error)}{" "}
          <button type="button" onClick={reloadAll} className="font-semibold underline">
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
          title={hasFilters ? t("expenses.emptySearch.title") : t("expenses.empty.title")}
          message={hasFilters ? t("expenses.emptySearch.message") : t("expenses.empty.message")}
        >
          {!hasFilters && (
            <Button onClick={() => setModal({ type: "form", expense: null })}>
              {t("expenses.add")}
            </Button>
          )}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={expenses.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              expenses.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((expense) => {
              const details = [
                formatDate(expense.expense_date),
                t(`method.${expense.payment_method}`),
                expense.supplier_name,
              ]
                .filter(Boolean)
                .join(" · ");
              return (
                <li
                  key={expense.id}
                  className="grid gap-3 border-b border-slate-200 p-4 last:border-b-0 md:grid-cols-[minmax(0,2fr)_1fr_auto] md:items-center"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{expense.description}</p>
                    <p className="text-sm text-slate-600">
                      {expense.category_name}
                      {!expense.category_affects_profit && (
                        <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-800">
                          {t("expenses.notInProfit")}
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-slate-600">{details}</p>
                  </div>
                  <p className="font-semibold text-slate-900 md:text-right">
                    {money(expense.amount)}
                  </p>
                  {deleteId === expense.id ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-800">
                        {t("expenses.confirmDelete")}
                      </span>
                      <Button variant="secondary" onClick={() => setDeleteId(null)}>
                        {t("expenses.keep")}
                      </Button>
                      <Button loading={deleting} onClick={() => handleDelete(expense)}>
                        {t("expenses.confirmYes")}
                      </Button>
                    </div>
                  ) : (
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        onClick={() => setModal({ type: "form", expense })}
                        aria-label={`${t("expenses.edit")}: ${expense.description}`}
                      >
                        {t("expenses.edit")}
                      </Button>
                      {canDelete && (
                        <Button
                          variant="ghost"
                          onClick={() => {
                            setDeleteId(expense.id);
                            setDeleteError("");
                          }}
                          aria-label={`${t("expenses.delete")}: ${expense.description}`}
                        >
                          {t("expenses.delete")}
                        </Button>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            disabled={expenses.loading}
          />
        </>
      )}

      {modal?.type === "form" && (
        <ExpenseFormModal
          expense={modal.expense}
          categories={categories.data?.results ?? []}
          suppliers={suppliers.data?.results ?? []}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
        />
      )}
      {modal?.type === "categories" && (
        <ExpenseCategoriesModal
          onClose={() => setModal(null)}
          onChanged={() => {
            categories.reload();
            reloadAll();
          }}
        />
      )}
    </>
  );
}
