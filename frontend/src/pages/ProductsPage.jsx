import { useState } from "react";
import { listCategories, listProducts } from "../api/inventory";
import CategoriesModal from "../components/products/CategoriesModal";
import ProductFormModal from "../components/products/ProductFormModal";
import ProductRow from "../components/products/ProductRow";
import StockAdjustModal from "../components/products/StockAdjustModal";
import StockHistoryModal from "../components/products/StockHistoryModal";
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

export default function ProductsPage() {
  const { role, business } = useAuth();
  const canManage = role !== ROLES.STAFF;

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [stockStatus, setStockStatus] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState("");

  const debouncedSearch = useDebounce(search.trim());
  const params = {
    search: debouncedSearch,
    category,
    stock_status: stockStatus,
    is_active: showInactive ? undefined : true,
    page,
    page_size: PAGE_SIZE,
  };
  const products = useFetch(() => listProducts(params), JSON.stringify(params));
  const categories = useFetch(() => listCategories(), "categories");

  const rows = products.data?.results ?? [];
  const pageCount = Math.ceil((products.data?.count ?? 0) / PAGE_SIZE);
  const hasFilters = Boolean(debouncedSearch || category || stockStatus || showInactive);
  const firstLoad = products.loading && !products.data;
  const isEmpty = !products.loading && !products.error && rows.length === 0;

  const closeModal = () => setModal(null);
  const handleSaved = (message) => {
    setModal(null);
    setNotice(message);
    products.reload();
  };
  const handleCategoriesChanged = () => {
    categories.reload();
    products.reload();
  };
  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
    setNotice("");
  };

  const categoryOptions = [
    { value: "", label: t("products.filter.allCategories") },
    ...(categories.data?.results ?? []).map((item) => ({ value: item.id, label: item.name })),
  ];
  const statusOptions = [
    { value: "", label: t("products.filter.allStatuses") },
    { value: "in_stock", label: t("products.status.in_stock") },
    { value: "low", label: t("products.status.low") },
    { value: "out", label: t("products.status.out") },
  ];

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {t("products.title")}
          </h1>
          <p className="mt-1 text-slate-600">{t("products.subtitle")}</p>
        </div>
        {canManage && (
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setModal({ type: "categories" })}>
              {t("products.categories")}
            </Button>
            <Button onClick={() => setModal({ type: "form", product: null })}>
              {t("products.add")}
            </Button>
          </div>
        )}
      </div>

      {notice && (
        <Alert variant="success" className="mb-4">
          {notice}
        </Alert>
      )}

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr]">
        <TextField
          label={t("products.searchLabel")}
          type="search"
          placeholder={t("products.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
            setNotice("");
          }}
        />
        <SelectField
          label={t("products.filter.category")}
          options={categoryOptions}
          value={category}
          onChange={changeFilter(setCategory)}
        />
        <SelectField
          label={t("products.filter.status")}
          options={statusOptions}
          value={stockStatus}
          onChange={changeFilter(setStockStatus)}
        />
        <label className="flex min-h-11 items-center gap-3 text-sm font-medium text-slate-800">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(event) => {
              setShowInactive(event.target.checked);
              setPage(1);
            }}
            className="h-5 w-5"
          />
          {t("products.filter.showInactive")}
        </label>
      </div>

      {products.error && (
        <Alert className="mb-4">
          {t("products.loadError")} {getErrorMessage(products.error)}{" "}
          <button type="button" onClick={products.reload} className="font-semibold underline">
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
          title={hasFilters ? t("products.emptySearch.title") : t("products.empty.title")}
          message={hasFilters ? t("products.emptySearch.message") : t("products.empty.message")}
        >
          {canManage && !hasFilters && (
            <Button onClick={() => setModal({ type: "form", product: null })}>
              {t("products.add")}
            </Button>
          )}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <ul
            aria-busy={products.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              products.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((product) => (
              <ProductRow
                key={product.id}
                product={product}
                currency={business.currency}
                canManage={canManage}
                onEdit={(item) => setModal({ type: "form", product: item })}
                onAdjust={(item) => setModal({ type: "stock", product: item })}
                onHistory={(item) => setModal({ type: "history", product: item })}
              />
            ))}
          </ul>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            disabled={products.loading}
          />
        </>
      )}

      {modal?.type === "form" && (
        <ProductFormModal
          product={modal.product}
          categories={categories.data?.results ?? []}
          onClose={closeModal}
          onSaved={handleSaved}
        />
      )}
      {modal?.type === "stock" && (
        <StockAdjustModal product={modal.product} onClose={closeModal} onSaved={handleSaved} />
      )}
      {modal?.type === "history" && (
        <StockHistoryModal product={modal.product} onClose={closeModal} />
      )}
      {modal?.type === "categories" && (
        <CategoriesModal onClose={closeModal} onChanged={handleCategoriesChanged} />
      )}
    </>
  );
}
