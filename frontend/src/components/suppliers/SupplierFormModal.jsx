import { useState } from "react";
import { createSupplier, updateSupplier } from "../../api/inventory";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import TextAreaField from "../ui/TextAreaField";
import TextField from "../ui/TextField";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function toForm(supplier) {
  return {
    name: supplier?.name ?? "",
    phone: supplier?.phone ?? "",
    email: supplier?.email ?? "",
    address: supplier?.address ?? "",
    notes: supplier?.notes ?? "",
  };
}

export default function SupplierFormModal({ supplier, onClose, onSaved }) {
  const isEdit = Boolean(supplier);
  const [form, setForm] = useState(toForm(supplier));
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
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

    setSubmitting(true);
    try {
      if (isEdit) await updateSupplier(supplier.id, payload);
      else await createSupplier(payload);
      onSaved(t("suppliers.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={isEdit ? t("supplierForm.editTitle") : t("supplierForm.addTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("field.supplierName")}
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
