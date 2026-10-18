import { useState } from "react";
import { createExpense, updateExpense } from "../../api/expenses";
import { PAYMENT_METHODS } from "../../config/options";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { todayISO } from "../../utils/format";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import SelectField from "../ui/SelectField";
import TextAreaField from "../ui/TextAreaField";
import TextField from "../ui/TextField";

function emptyForm() {
  return {
    description: "",
    category: "",
    amount: "",
    expense_date: todayISO(),
    payment_method: "CASH",
    supplier: "",
    notes: "",
  };
}

function toForm(expense) {
  return {
    description: expense.description,
    category: expense.category,
    amount: expense.amount,
    expense_date: expense.expense_date,
    payment_method: expense.payment_method,
    supplier: expense.supplier ?? "",
    notes: expense.notes ?? "",
  };
}

export default function ExpenseFormModal({ expense, categories, suppliers, onClose, onSaved }) {
  const isEdit = Boolean(expense);
  const [form, setForm] = useState(isEdit ? toForm(expense) : emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const categoryOptions = [
    { value: "", label: t("field.chooseCategory") },
    ...categories.map((category) => ({ value: category.id, label: category.name })),
  ];
  const supplierOptions = [
    { value: "", label: t("field.noSupplier") },
    ...suppliers.map((supplier) => ({ value: supplier.id, label: supplier.name })),
  ];
  const methodOptions = PAYMENT_METHODS.map((value) => ({ value, label: t(`method.${value}`) }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!form.description.trim()) errors.description = t("validation.required");
    if (!form.category) errors.category = t("validation.categoryRequired");
    if (!isValidDecimal(form.amount, 2) || Number(form.amount) <= 0) {
      errors.amount = t("validation.amount");
    }
    if (!form.expense_date) errors.expense_date = t("validation.required");
    else if (form.expense_date > todayISO()) errors.expense_date = t("validation.dateFuture");
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      description: form.description.trim(),
      category: form.category,
      amount: form.amount.trim(),
      expense_date: form.expense_date,
      payment_method: form.payment_method,
      supplier: form.supplier || null,
      notes: form.notes.trim(),
    };

    setSubmitting(true);
    try {
      if (isEdit) await updateExpense(expense.id, payload);
      else await createExpense(payload);
      onSaved(t("expenses.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={isEdit ? t("expenseForm.editTitle") : t("expenseForm.addTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("field.expenseDescription")}
          name="description"
          autoComplete="off"
          required
          value={form.description}
          onChange={handleChange}
          error={fieldErrors.description}
        />
        <SelectField
          label={t("field.expenseCategory")}
          name="category"
          options={categoryOptions}
          value={form.category}
          onChange={handleChange}
          error={fieldErrors.category}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("field.expenseAmount")}
            name="amount"
            inputMode="decimal"
            required
            value={form.amount}
            onChange={handleChange}
            error={fieldErrors.amount}
          />
          <TextField
            label={t("field.expenseDate")}
            name="expense_date"
            type="date"
            max={todayISO()}
            required
            value={form.expense_date}
            onChange={handleChange}
            error={fieldErrors.expense_date}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label={t("field.paidWith")}
            name="payment_method"
            options={methodOptions}
            value={form.payment_method}
            onChange={handleChange}
            error={fieldErrors.payment_method}
          />
          <SelectField
            label={t("field.expenseSupplier")}
            name="supplier"
            options={supplierOptions}
            value={form.supplier}
            onChange={handleChange}
            error={fieldErrors.supplier}
          />
        </div>
        <TextAreaField
          label={t("field.expenseNotes")}
          name="notes"
          value={form.notes}
          onChange={handleChange}
          error={fieldErrors.notes}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" loading={submitting}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
