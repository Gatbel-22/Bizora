import { useState } from "react";
import { createReceivable } from "../../api/customers";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { todayISO } from "../../utils/format";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import TextField from "../ui/TextField";

export default function AddDebtModal({ customer, onClose, onSaved }) {
  const [form, setForm] = useState({
    original_amount: "",
    issue_date: todayISO(),
    due_date: "",
    note: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!isValidDecimal(form.original_amount, 2) || Number(form.original_amount) <= 0) {
      errors.original_amount = t("validation.amount");
    }
    if (!form.issue_date) errors.issue_date = t("validation.required");
    if (form.due_date && form.issue_date && form.due_date < form.issue_date) {
      errors.due_date = t("validation.dueBeforeIssue");
    }
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      customer: customer.id,
      original_amount: form.original_amount.trim(),
      issue_date: form.issue_date,
      note: form.note.trim(),
    };
    if (form.due_date) payload.due_date = form.due_date;

    setSubmitting(true);
    try {
      await createReceivable(payload);
      onSaved(t("debt.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal title={t("debt.title", { name: customer.name })} onClose={onClose}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("debt.amount")}
          name="original_amount"
          inputMode="decimal"
          required
          value={form.original_amount}
          onChange={handleChange}
          error={fieldErrors.original_amount}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("debt.issueDate")}
            name="issue_date"
            type="date"
            required
            value={form.issue_date}
            onChange={handleChange}
            error={fieldErrors.issue_date}
          />
          <TextField
            label={t("debt.dueDate")}
            name="due_date"
            type="date"
            value={form.due_date}
            onChange={handleChange}
            error={fieldErrors.due_date}
          />
        </div>
        <TextField
          label={t("debt.note")}
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
            {t("debt.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
