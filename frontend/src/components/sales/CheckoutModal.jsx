import { useState } from "react";
import { createSale } from "../../api/sales";
import { SALE_PAYMENT_METHODS } from "../../config/options";
import { t } from "../../i18n";
import { buildSalePayload, round2, saleTotals } from "../../utils/cart";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { formatMoney, todayISO } from "../../utils/format";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import TextField from "../ui/TextField";
import CustomerPicker from "./CustomerPicker";
import CustomerFormModal from "../customers/CustomerFormModal";

// One reference per checkout. If a request has to be retried, the server recognises it
// and returns the sale it already saved instead of creating a second one.
function newReference() {
  return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : undefined;
}

export default function CheckoutModal({ cart, currency, onClose, onDone }) {
  const [customer, setCustomer] = useState(null);
  const [addingCustomer, setAddingCustomer] = useState(false);
  const [discount, setDiscount] = useState("");
  const [method, setMethod] = useState("CASH");
  const [amountPaid, setAmountPaid] = useState(null); // null means "paid in full"
  const [dueDate, setDueDate] = useState("");
  const [note, setNote] = useState("");
  const [reference] = useState(newReference);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const totals = saleTotals(cart, discount);
  const isCredit = method === "CREDIT";
  const paidText = amountPaid ?? totals.total.toFixed(2);
  const paid = isCredit ? 0 : Number(paidText);
  const balance = Number.isFinite(paid) ? round2(totals.total - paid) : 0;
  const money = (value) => formatMoney(value, currency);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (discount.trim() && !isValidDecimal(discount, 2)) errors.discount = t("validation.amount");
    else if (totals.discount > totals.subtotal) errors.discount = t("checkout.discountTooBig");
    if (!isCredit) {
      if (!isValidDecimal(paidText, 2) || Number(paidText) <= 0) {
        errors.amount_paid = t("validation.amount");
      } else if (Number(paidText) > totals.total) {
        errors.amount_paid = t("checkout.amountTooBig");
      }
    }
    if (balance > 0 && !customer) errors.customer = t("checkout.customerRequired");
    if (balance > 0 && dueDate && dueDate < todayISO()) errors.due_date = t("checkout.dueInPast");
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = buildSalePayload({
      cart,
      customerId: customer?.id,
      discount,
      paymentMethod: method,
      amountPaid: paidText,
      dueDate: balance > 0 ? dueDate : "",
      note,
      clientReference: reference,
    });

    setSubmitting(true);
    try {
      onDone(await createSale(payload));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      // Stock problems come back against "items": show them as the main message.
      setFormError(
        serverErrors.items || (Object.keys(serverErrors).length === 0 ? getErrorMessage(error) : "")
      );
      setSubmitting(false);
    }
  };

  return (
    <>
      <Modal title={t("checkout.title")} onClose={onClose}>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {formError && <Alert>{formError}</Alert>}

          <dl className="space-y-1 rounded-lg bg-slate-50 p-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-700">{t("checkout.subtotal")}</dt>
              <dd className="font-medium text-slate-900">{money(totals.subtotal)}</dd>
            </div>
            {totals.discount > 0 && (
              <div className="flex justify-between">
                <dt className="text-slate-700">{t("checkout.discountLine")}</dt>
                <dd className="font-medium text-slate-900">-{money(totals.discount)}</dd>
              </div>
            )}
            <div className="flex justify-between text-base">
              <dt className="font-semibold text-slate-900">{t("checkout.total")}</dt>
              <dd className="font-bold text-slate-900">{money(totals.total)}</dd>
            </div>
            {balance > 0 && (
              <>
                <div className="flex justify-between">
                  <dt className="text-slate-700">{t("checkout.paidNow")}</dt>
                  <dd className="font-medium text-slate-900">{money(paid)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-700">{t("checkout.balance")}</dt>
                  <dd className="font-semibold text-red-700">{money(balance)}</dd>
                </div>
              </>
            )}
          </dl>

          <fieldset>
            <legend className="text-sm font-medium text-slate-800">
              {t("checkout.paymentMethod")}
            </legend>
            <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {SALE_PAYMENT_METHODS.map((value) => {
                const selected = method === value;
                return (
                  <label
                    key={value}
                    className={`flex min-h-11 cursor-pointer items-center justify-center rounded-lg border px-3 text-sm font-semibold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand-600 ${
                      selected
                        ? "border-brand-700 bg-brand-50 text-brand-900"
                        : "border-slate-300 bg-white text-slate-800"
                    }`}
                  >
                    <input
                      type="radio"
                      name="payment_method"
                      value={value}
                      checked={selected}
                      onChange={() => setMethod(value)}
                      className="sr-only"
                    />
                    {t(`method.${value}`)}
                  </label>
                );
              })}
            </div>
          </fieldset>

          {isCredit ? (
            <p className="text-sm text-slate-700">{t("checkout.creditNote")}</p>
          ) : (
            <TextField
              label={t("checkout.amountPaid")}
              inputMode="decimal"
              value={paidText}
              onChange={(event) => setAmountPaid(event.target.value)}
              error={fieldErrors.amount_paid}
            />
          )}

          <div>
            <p className="mb-1 text-sm font-medium text-slate-800">{t("checkout.customer")}</p>
            <p className="mb-2 text-sm text-slate-600">{t("checkout.customerHint")}</p>
            <CustomerPicker
              value={customer}
              onChange={setCustomer}
              onAddNew={() => setAddingCustomer(true)}
              error={fieldErrors.customer}
              currency={currency}
            />
          </div>

          {balance > 0 && (
            <TextField
              label={t("checkout.dueDate")}
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.target.value)}
              error={fieldErrors.due_date}
            />
          )}

          <TextField
            label={t("checkout.discount")}
            inputMode="decimal"
            value={discount}
            onChange={(event) => setDiscount(event.target.value)}
            error={fieldErrors.discount}
          />
          <TextField
            label={t("checkout.note")}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            error={fieldErrors.note}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={submitting}>
              {t("checkout.submit")}
            </Button>
          </div>
        </form>
      </Modal>

      {addingCustomer && (
        <CustomerFormModal
          customer={null}
          onClose={() => setAddingCustomer(false)}
          onSaved={(_message, saved) => {
            setAddingCustomer(false);
            setCustomer(saved);
          }}
        />
      )}
    </>
  );
}
