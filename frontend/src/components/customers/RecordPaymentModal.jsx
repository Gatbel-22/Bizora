import { useState } from "react";
import { recordCustomerPayment } from "../../api/customers";
import { PAYMENT_METHODS } from "../../config/options";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { formatDate, formatMoney } from "../../utils/format";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import SelectField from "../ui/SelectField";
import TextField from "../ui/TextField";

export default function RecordPaymentModal({ customer, openDebts, currency, onClose, onSaved }) {
  const owed = Number(customer.outstanding_balance);
  const [form, setForm] = useState({ amount: "", method: "CASH", receivable: "", note: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const methodOptions = PAYMENT_METHODS.map((value) => ({ value, label: t(`method.${value}`) }));
  const debtOptions = [
    { value: "", label: t("payment.oldestFirst") },
    ...openDebts.map((debt) => ({
      value: debt.id,
      label: t("payment.debtOption", {
        balance: formatMoney(debt.balance, currency),
        date: formatDate(debt.issue_date),
      }),
    })),
  ];

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!isValidDecimal(form.amount, 2) || Number(form.amount) <= 0) {
      errors.amount = t("validation.amount");
    } else if (Number(form.amount) > owed) {
      errors.amount = t("payment.tooMuch", { amount: formatMoney(owed, currency) });
    }
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      customer: customer.id,
      amount: form.amount.trim(),
      method: form.method,
      note: form.note.trim(),
    };
    if (form.receivable) payload.receivable = form.receivable;

    setSubmitting(true);
    try {
      await recordCustomerPayment(payload);
      onSaved(t("payment.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal title={t("payment.title", { name: customer.name })} onClose={onClose}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <p className="text-sm text-slate-700">
          {t("payment.owed", { amount: formatMoney(owed, currency) })}
        </p>
        {formError && <Alert>{formError}</Alert>}
        <div>
          <TextField
            label={t("payment.amount")}
            name="amount"
            inputMode="decimal"
            required
            value={form.amount}
            onChange={handleChange}
            error={fieldErrors.amount}
          />
          {!form.receivable && (
            <button
              type="button"
              onClick={() =>
                setForm((current) => ({ ...current, amount: customer.outstanding_balance }))
              }
              className="mt-1 min-h-11 text-sm font-semibold text-brand-700 underline"
            >
              {t("payment.payFull")}
            </button>
          )}
        </div>
        <SelectField
          label={t("payment.method")}
          name="method"
          options={methodOptions}
          value={form.method}
          onChange={handleChange}
          error={fieldErrors.method}
        />
        {openDebts.length > 1 && (
          <SelectField
            label={t("payment.applyTo")}
            name="receivable"
            options={debtOptions}
            value={form.receivable}
            onChange={handleChange}
            error={fieldErrors.receivable}
          />
        )}
        <TextField
          label={t("payment.note")}
          name="note"
          value={form.note}
          onChange={handleChange}
          error={fieldErrors.note}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" loading={submitting}>
            {t("payment.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
