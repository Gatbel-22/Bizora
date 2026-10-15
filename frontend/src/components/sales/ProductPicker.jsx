import { useState } from "react";
import { listProducts } from "../../api/inventory";
import { UNIT_LABELS } from "../../config/options";
import useAuth from "../../hooks/useAuth";
import useDebounce from "../../hooks/useDebounce";
import useFetch from "../../hooks/useFetch";
import { t } from "../../i18n";
import { getErrorMessage } from "../../utils/errors";
import { formatMoney, formatQuantity } from "../../utils/format";
import Alert from "../ui/Alert";
import Spinner from "../ui/Spinner";
import TextField from "../ui/TextField";

export default function ProductPicker({ onPick, quantities }) {
  const { business } = useAuth();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search.trim(), 300);
  const params = { search: debouncedSearch, is_active: true, page_size: 8 };
  const products = useFetch(() => listProducts(params), JSON.stringify(params));
  const rows = products.data?.results ?? [];

  return (
    <section aria-label={t("newSale.searchLabel")}>
      <TextField
        label={t("newSale.searchLabel")}
        type="search"
        autoComplete="off"
        placeholder={t("newSale.searchPlaceholder")}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      <div className="mt-3">
        {products.error && (
          <Alert className="mb-3">
            {t("newSale.loadError")} {getErrorMessage(products.error)}{" "}
            <button type="button" onClick={products.reload} className="font-semibold underline">
              {t("common.tryAgain")}
            </button>
          </Alert>
        )}
        {products.loading && !products.data && (
          <div role="status" className="flex justify-center py-8 text-brand-700">
            <Spinner className="h-6 w-6" />
          </div>
        )}
        {products.data && rows.length === 0 && (
          <p className="py-6 text-center text-sm text-slate-600">{t("newSale.noProducts")}</p>
        )}
        {rows.length > 0 && (
          <ul
            aria-busy={products.loading}
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-opacity ${
              products.loading ? "opacity-60" : ""
            }`}
          >
            {rows.map((product) => {
              const out = product.stock_status === "out";
              const inCart = quantities[product.id];
              return (
                <li key={product.id} className="border-b border-slate-200 last:border-b-0">
                  <button
                    type="button"
                    disabled={out}
                    onClick={() => onPick(product)}
                    className="flex min-h-14 w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className="min-w-0">
                      <span className="block font-semibold text-slate-900">{product.name}</span>
                      <span className="block text-sm text-slate-600">
                        {formatMoney(product.selling_price, business.currency)} ·{" "}
                        {out
                          ? t("newSale.outOfStock")
                          : t("newSale.inStock", {
                              qty: formatQuantity(product.current_stock),
                              unit: UNIT_LABELS[product.unit] ?? "",
                            })}
                      </span>
                    </span>
                    {inCart && (
                      <span className="shrink-0 rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-semibold text-brand-900">
                        {t("newSale.inCart", { count: inCart })}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
