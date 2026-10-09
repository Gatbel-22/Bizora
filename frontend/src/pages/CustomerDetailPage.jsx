import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCustomer, listCustomerPayments, listReceivables } from "../api/customers";
import AddDebtModal from "../components/customers/AddDebtModal";
import CustomerFormModal from "../components/customers/CustomerFormModal";
import RecordPaymentModal from "../components/customers/RecordPaymentModal";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import DebtStatusBadge from "../components/ui/DebtStatusBadge";
import EmptyState from "../components/ui/EmptyState";
import FullPageMessage from "../components/ui/FullPageMessage";
import Spinner from "../components/ui/Spinner";
import { ROLES } from "../config/roles";
import useAuth from "../hooks/useAuth";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { formatDate, formatDateTime, formatMoney } from "../utils/format";

function LoadError({ error, onRetry }) {
  return (
    <Alert>
      {t("customer.loadError")} {getErrorMessage(error)}{" "}
      <button type="button" onClick={onRetry} className="font-semibold underline">
        {t("common.tryAgain")}
      </button>
    </Alert>
  );
}

function Loading() {
  return (
    <div role="status" className="flex justify-center py-8 text-brand-700">
      <Spinner className="h-6 w-6" />
    </div>
  );
}

export default function CustomerDetailPage() {
  const { id } = useParams();
  const { role, business } = useAuth();
  const canManage = role !== ROLES.STAFF;
  const currency = business.currency;

  const [showPaid, setShowPaid] = useState(false);
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState("");

  const customer = useFetch(() => getCustomer(id), `customer-${id}`);
  const debts = useFetch(
    () =>
      listReceivables({
        customer: id,
        is_open: showPaid ? undefined : true,
        ordering: "due_date",
        page_size: 50,
      }),
    `debts-${id}-${showPaid}`
  );
  const payments = useFetch(
    () => listCustomerPayments({ customer: id, page_size: 25 }),
    `payments-${id}`
  );

  const handleSaved = (message) => {
    setModal(null);
    setNotice(message);
    customer.reload();
    debts.reload();
    payments.reload();
  };

  if (customer.error && !customer.data) {
    const notFound = customer.error.response?.status === 404;
    return (
      <FullPageMessage
        fullScreen={false}
        title={notFound ? t("customer.notFound") : t("customers.loadError")}
        message={notFound ? t("customer.notFoundMessage") : getErrorMessage(customer.error)}
      >
        <div className="flex flex-col items-center gap-3">
          {!notFound && <Button onClick={customer.reload}>{t("common.tryAgain")}</Button>}
          <Link to="/customers" className="font-semibold text-brand-700 underline">
            {t("customer.back")}
          </Link>
        </div>
      </FullPageMessage>
    );
  }

  if (!customer.data) return <Loading />;

  const c = customer.data;
  const owes = Number(c.outstanding_balance) > 0;
  const openDebts = (debts.data?.results ?? []).filter((debt) => debt.status !== "paid");
  const debtRows = debts.data?.results ?? [];
  const paymentRows = payments.data?.results ?? [];
  const contact = [c.phone, c.email, c.address].filter(Boolean);

  return (
    <>
      <Link to="/customers" className="text-sm font-semibold text-brand-700 underline">
        {t("customer.back")}
      </Link>

      <div className="mb-6 mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {c.name}
            {!c.is_active && (
              <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-800">
                {t("customers.inactive")}
              </span>
            )}
          </h1>
          {contact.length > 0 && <p className="mt-1 text-slate-600">{contact.join(" · ")}</p>}
          {c.notes && <p className="mt-1 text-sm text-slate-700">{c.notes}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {owes && (
            <Button onClick={() => setModal("payment")}>{t("customer.recordPayment")}</Button>
          )}
          {canManage && (
            <>
              <Button variant="secondary" onClick={() => setModal("debt")}>
                {t("customer.addDebt")}
              </Button>
              <Button variant="ghost" onClick={() => setModal("edit")}>
                {t("customers.edit")}
              </Button>
            </>
          )}
        </div>
      </div>

      {notice && (
        <Alert variant="success" className="mb-4">
          {notice}
        </Alert>
      )}

      <div className="mb-8 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-600">{t("customer.outstanding")}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {formatMoney(c.outstanding_balance, currency)}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-600">{t("customer.overdue")}</p>
          <p
            className={`mt-1 text-2xl font-bold ${
              Number(c.overdue_balance) > 0 ? "text-red-700" : "text-slate-900"
            }`}
          >
            {formatMoney(c.overdue_balance, currency)}
          </p>
        </div>
      </div>

      <section aria-labelledby="debts-heading" className="mb-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="debts-heading" className="text-lg font-semibold text-slate-900">
            {t("customer.debts")}
          </h2>
          <label className="flex min-h-11 items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={showPaid}
              onChange={(event) => setShowPaid(event.target.checked)}
              className="h-5 w-5"
            />
            {t("customer.showPaid")}
          </label>
        </div>

        {debts.error && <LoadError error={debts.error} onRetry={debts.reload} />}
        {debts.loading && !debts.data && <Loading />}
        {debts.data && debtRows.length === 0 && (
          <EmptyState title={t("customer.noDebts.title")} message={t("customer.noDebts.message")} />
        )}
        {debtRows.length > 0 && (
          <ul className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            {debtRows.map((debt) => (
              <li
                key={debt.id}
                className="grid gap-2 border-b border-slate-200 p-4 last:border-b-0 sm:grid-cols-[1fr_auto]"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <DebtStatusBadge status={debt.status} />
                    <span className="text-sm text-slate-700">
                      {debt.due_date
                        ? t("customer.debt.due", { date: formatDate(debt.due_date) })
                        : t("customer.debt.noDue")}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {t("customer.debt.issued", { date: formatDate(debt.issue_date) })}
                    {debt.days_outstanding !== null &&
                      ` · ${t("customer.debt.days", { days: debt.days_outstanding })}`}
                  </p>
                  {debt.note && <p className="text-sm text-slate-700">{debt.note}</p>}
                </div>
                <div className="text-sm sm:text-right">
                  <p className="font-semibold text-slate-900">
                    {t("customer.debt.balance")}: {formatMoney(debt.balance, currency)}
                  </p>
                  <p className="text-slate-600">
                    {t("customer.debt.original")}: {formatMoney(debt.original_amount, currency)}
                  </p>
                  <p className="text-slate-600">
                    {t("customer.debt.paid")}: {formatMoney(debt.amount_paid, currency)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="payments-heading">
        <h2 id="payments-heading" className="mb-3 text-lg font-semibold text-slate-900">
          {t("customer.payments")}
        </h2>
        {payments.error && <LoadError error={payments.error} onRetry={payments.reload} />}
        {payments.loading && !payments.data && <Loading />}
        {payments.data && paymentRows.length === 0 && (
          <p className="text-sm text-slate-600">{t("customer.noPayments")}</p>
        )}
        {paymentRows.length > 0 && (
          <ul className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            {paymentRows.map((payment) => (
              <li
                key={payment.id}
                className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 p-4 last:border-b-0"
              >
                <div>
                  <p className="font-semibold text-slate-900">
                    {formatMoney(payment.amount, currency)}{" "}
                    <span className="font-normal text-slate-600">
                      · {t(`method.${payment.method}`)}
                    </span>
                  </p>
                  <p className="text-sm text-slate-600">
                    {formatDateTime(payment.created_at)}
                    {payment.created_by_name &&
                      ` · ${t("history.by", { name: payment.created_by_name })}`}
                  </p>
                  {payment.note && <p className="text-sm text-slate-700">{payment.note}</p>}
                </div>
                <p className="text-sm text-slate-600">
                  {t("customer.payment.appliedTo", { count: payment.allocations.length })}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {modal === "payment" && (
        <RecordPaymentModal
          customer={c}
          openDebts={openDebts}
          currency={currency}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
        />
      )}
      {modal === "debt" && (
        <AddDebtModal customer={c} onClose={() => setModal(null)} onSaved={handleSaved} />
      )}
      {modal === "edit" && (
        <CustomerFormModal customer={c} onClose={() => setModal(null)} onSaved={handleSaved} />
      )}
    </>
  );
}
