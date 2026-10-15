import { useState } from "react";
import { cancelSale } from "../../api/sales";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import TextAreaField from "../ui/TextAreaField";

export default function CancelSaleModal({ sale, onClose, onCancelled }) {
  const [reason, setReason] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    if (!reason.trim()) {
      setFieldError(t("validation.required"));
      return;
    }
    setFieldError("");
    setSubmitting(true);
    try {
      await cancelSale(sale.id, reason.trim());
      onCancelled();
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      if (serverErrors.reason) setFieldError(serverErrors.reason);
      else setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal title={t("cancel.title", { number: sale.number })} onClose={onClose}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <p className="text-sm text-slate-700">{t("cancel.warning")}</p>
        {formError && <Alert>{formError}</Alert>}
        <TextAreaField
          label={t("cancel.reason")}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          error={fieldError}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            {t("cancel.keep")}
          </Button>
          <Button type="submit" loading={submitting}>
            {t("cancel.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
