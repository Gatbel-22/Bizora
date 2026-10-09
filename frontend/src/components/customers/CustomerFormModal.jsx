import { useState } from "react";
import { createCustomer, updateCustomer } from "../../api/customers";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import TextAreaField from "../ui/TextAreaField";
import TextField from "../ui/TextField";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function toForm(customer) {
  return {
    name: customer?.name ?? "",
    phone: customer?.phone ?? "",
    email: customer?.email ?? "",
    address: customer?.address ?? "",
    notes: customer?.notes ?? "",
    is_active: customer?.is_active ?? true,
  };
}

export default function CustomerFormModal({ customer, onClose, onSaved }) {
  const isEdit = Boolean(customer);
  const [form, setForm] = useState(toForm(customer));
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!form.name.trim()) errors.name = t("validation.required");
    if (form.email.trim() && !EMAIL_PATTERN.test(form.email.trim())) {
      errors.email = t("validation.emailInvalid");
    }
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      name: form.name.trim(),
      phone: form.phone.trim(),
      email: form.email.trim(),
      address: form.address.trim(),
      notes: form.notes.trim(),
    };
    if (isEdit) payload.is_active = form.is_active;

    setSubmitting(true);
    try {
      if (isEdit) await updateCustomer(customer.id, payload);
      else await createCustomer(payload);
      onSaved(t("customers.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={isEdit ? t("customerForm.editTitle") : t("customerForm.addTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("field.customerName")}
          name="name"
          autoComplete="off"
          required
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("field.phone")}
            name="phone"
            type="tel"
            inputMode="tel"
            value={form.phone}
            onChange={handleChange}
            error={fieldErrors.phone}
          />
          <TextField
            label={t("field.email")}
            name="email"
            type="email"
            inputMode="email"
            value={form.email}
            onChange={handleChange}
            error={fieldErrors.email}
          />
        </div>
        <TextAreaField
          label={t("field.address")}
          name="address"
          value={form.address}
          onChange={handleChange}
          error={fieldErrors.address}
        />
        <TextAreaField
          label={t("field.notes")}
          name="notes"
          value={form.notes}
          onChange={handleChange}
          error={fieldErrors.notes}
        />
        {isEdit && (
          <label className="flex min-h-11 items-center gap-3 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
              className="h-5 w-5"
            />
            {t("field.customerActive")}
          </label>
        )}
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
