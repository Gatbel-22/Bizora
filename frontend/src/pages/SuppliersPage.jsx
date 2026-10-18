import { useState } from "react";
import { deleteSupplier, listSuppliers } from "../api/inventory";
import SupplierFormModal from "../components/suppliers/SupplierFormModal";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import Spinner from "../components/ui/Spinner";
import TextField from "../components/ui/TextField";
import { PAGE_SIZE } from "../config/pagination";
import useDebounce from "../hooks/useDebounce";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";

export default function SuppliersPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState("");
  const [deleteId, setDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const debouncedSearch = useDebounce(search.trim());
  const params = { search: debouncedSearch, page, page_size: PAGE_SIZE };
  const suppliers = useFetch(() => listSuppliers(params), JSON.stringify(params));

  const rows = suppliers.data?.results ?? [];
  const pageCount = Math.ceil((suppliers.data?.count ?? 0) / PAGE_SIZE);
  const hasFilters = Boolean(debouncedSearch);
  const firstLoad = suppliers.loading && !suppliers.data;
  const isEmpty = !suppliers.loading && !suppliers.error && rows.length === 0;

  const handleSaved = (message) => {
    setModal(null);
    setNotice(message);
    suppliers.reload();
  };

  const handleDelete = async (supplier) => {
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteSupplier(supplier.id);
      setDeleteId(null);
      setNotice(t("suppliers.deleted"));
      suppliers.reload();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setDeleteId(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {t("suppliers.title")}
          </h1>
          <p className="mt-1 text-slate-600">{t("suppliers.subtitle")}</p>
        </div>
        <Button onClick={() => setModal({ supplier: null })}>{t("suppliers.add")}</Button>
      </div>

      {notice && (
        <Alert variant="success" className="mb-4">
          {notice}
        </Alert>
      )}
      {deleteError && <Alert className="mb-4">{deleteError}</Alert>}

      <div className="mb-4 max-w-md">
        <TextField
          label={t("suppliers.searchLabel")}
          type="search"
          placeholder={t("suppliers.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
            setNotice("");
          }}
        />
      </div>

      {suppliers.error && (
        <Alert className="mb-4">
          {t("suppliers.loadError")} {getErrorMessage(suppliers.error)}{" "}
          <button type="button" onClick={suppliers.reload} className="font-semibold underline">
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
          title={hasFilters ? t("suppliers.emptySearch.title") : t("suppliers.empty.title")}
          message={hasFilters ? t("suppliers.emptySearch.message") : t("suppliers.empty.message")}
        >
          {!hasFilters && (
            <Button onClick={() => setModal({ supplier: null })}>{t("suppliers.add")}</Button>
          )}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={suppliers.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              suppliers.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((supplier) => {
              const contact = [supplier.phone, supplier.email].filter(Boolean).join(" · ");
              return (
                <li
                  key={supplier.id}
                  className="grid gap-3 border-b border-slate-200 p-4 last:border-b-0 md:grid-cols-[minmax(0,2fr)_1fr_auto] md:items-center"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{supplier.name}</p>
                    {contact && <p className="truncate text-sm text-slate-600">{contact}</p>}
                  </div>
                  <p className="text-sm text-slate-600">
                    {t("suppliers.products", { count: supplier.product_count ?? 0 })}
                  </p>
                  {deleteId === supplier.id ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-800">
                        {t("suppliers.confirm", { name: supplier.name })}
                      </span>
                      <Button variant="secondary" onClick={() => setDeleteId(null)}>
                        {t("suppliers.keep")}
                      </Button>
                      <Button loading={deleting} onClick={() => handleDelete(supplier)}>
                        {t("suppliers.confirmYes")}
                      </Button>
                    </div>
                  ) : (
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        onClick={() => setModal({ supplier })}
                        aria-label={`${t("suppliers.edit")}: ${supplier.name}`}
                      >
                        {t("suppliers.edit")}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setDeleteId(supplier.id);
                          setDeleteError("");
                        }}
                        aria-label={`${t("suppliers.delete")}: ${supplier.name}`}
                      >
                        {t("suppliers.delete")}
                      </Button>
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
            disabled={suppliers.loading}
          />
        </>
      )}

      {modal && (
        <SupplierFormModal
          supplier={modal.supplier}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
