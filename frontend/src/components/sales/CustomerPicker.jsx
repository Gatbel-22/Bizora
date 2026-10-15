import { useState } from "react";
import { listCustomers } from "../../api/customers";
import useDebounce from "../../hooks/useDebounce";
import useFetch from "../../hooks/useFetch";
import { t } from "../../i18n";
import { formatMoney } from "../../utils/format";
import Button from "../ui/Button";
import TextField from "../ui/TextField";

export default function CustomerPicker({ value, onChange, onAddNew, error, currency }) {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search.trim(), 300);
  const params = { search: debouncedSearch, is_active: true, page_size: 5 };
  const results = useFetch(() => listCustomers(params), JSON.stringify(params));
  const rows = results.data?.results ?? [];

  if (value) {
    const owes = Number(value.outstanding_balance) > 0;
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-300 bg-white px-3 py-2">
        <div className="min-w-0">
          <p className="font-semibold text-slate-900">{value.name}</p>
          {owes && (
            <p className="text-sm text-slate-600">
              {t("checkout.owes", { amount: formatMoney(value.outstanding_balance, currency) })}
            </p>
          )}
        </div>
        <Button variant="ghost" onClick={() => onChange(null)}>
          {t("checkout.removeCustomer")}
        </Button>
      </div>
    );
  }

  return (
    <div>
      <TextField
        label={t("checkout.searchCustomer")}
        type="search"
        autoComplete="off"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        error={error}
      />
      <ul className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white">
        {rows.map((customer) => (
          <li key={customer.id} className="border-b border-slate-200 last:border-b-0">
            <button
              type="button"
              onClick={() => onChange(customer)}
              className="flex min-h-11 w-full items-center justify-between px-3 py-2 text-left hover:bg-slate-50"
            >
              <span className="font-medium text-slate-900">{customer.name}</span>
              {customer.phone && <span className="text-sm text-slate-600">{customer.phone}</span>}
            </button>
          </li>
        ))}
        {results.data && rows.length === 0 && (
          <li className="px-3 py-2 text-sm text-slate-600">{t("checkout.noCustomers")}</li>
        )}
      </ul>
      <Button variant="secondary" onClick={onAddNew} className="mt-2">
        {t("checkout.newCustomer")}
      </Button>
    </div>
  );
}
