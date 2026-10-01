import { useState } from "react";
import { adjustStock } from "../../api/inventory";
import { UNIT_LABELS } from "../../config/options";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { formatQuantity } from "../../utils/format";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import SelectField from "../ui/SelectField";
import TextField from "../ui/TextField";

const TYPES = ["STOCK_IN", "STOCK_OUT", "COUNT"];

function previewStock(current, type, rawQuantity) {
  if (!isValidDecimal(rawQuantity, 3)) return null;
  const quantity = Number(rawQuantity);
  const stock = Number(current);
  if (type === "STOCK_IN") return stock + quantity;
  if (type === "STOCK_OUT") return stock - quantity;
  return quantity;
}

export default function StockAdjustModal({ product, onClose, onSaved }) {
  const [form, setForm] = useState({
    adjustment_type: "STOCK_IN",
    quantity: "",
    note: "",
    unit_cost: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const type = form.adjustment_type;
  const unit = UNIT_LABELS[product.unit] ?? "";
  const preview = previewStock(product.current_stock, type, form.quantity);
  const typeOptions = TYPES.map((value) => ({ value, label: t(`stock.type.${value}`) }));

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!isValidDecimal(form.quantity, 3)) errors.quantity = t("validation.quantity");
    else if (type !== "COUNT" && Number(form.quantity) <= 0) {
      errors.quantity = t("validation.quantityPositive");
    }
    if (type !== "STOCK_IN" && !form.note.trim()) errors.note = t("validation.reason");
    if (type === "STOCK_IN" && form.unit_cost.trim() && !isValidDecimal(form.unit_cost, 2)) {
      errors.unit_cost = t("validation.amount");
    }
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      adjustment_type: type,
      quantity: form.quantity.trim(),
      note: form.note.trim(),
    };
    if (type === "STOCK_IN" && form.unit_cost.trim()) payload.unit_cost = form.unit_cost.trim();

    setSubmitting(true);
    try {
      await adjustStock(product.id, payload);
      onSaved(t("products.stockUpdated"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <Modal title={t("stock.title", { name: product.name })} onClose={onClose}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <p className="text-sm text-slate-700">
          {t("stock.current", { qty: formatQuantity(product.current_stock), unit })}
        </p>
        {formError && <Alert>{formError}</Alert>}
        <SelectField
          label={t("stock.type")}
          name="adjustment_type"
          options={typeOptions}
          value={type}
          onChange={handleChange}
          error={fieldErrors.adjustment_type}
        />
        <TextField
          label={t(`stock.quantity.${type}`)}
          name="quantity"
          inputMode="decimal"
          required
          value={form.quantity}
          onChange={handleChange}
          error={fieldErrors.quantity}
        />
        {preview !== null && (
          <p
            aria-live="polite"
            className={`text-sm font-medium ${preview < 0 ? "text-red-700" : "text-slate-800"}`}
          >
            {preview < 0
              ? t("stock.previewNegative")
              : t("stock.preview", { qty: formatQuantity(preview), unit })}
          </p>
        )}
        {type === "STOCK_IN" && (
          <TextField
            label={t("stock.unitCost")}
            name="unit_cost"
            inputMode="decimal"
            value={form.unit_cost}
            onChange={handleChange}
            error={fieldErrors.unit_cost}
          />
        )}
        <TextField
          label={t("stock.note")}
          name="note"
          required={type !== "STOCK_IN"}
          value={form.note}
          onChange={handleChange}
          error={fieldErrors.note}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" loading={submitting}>
            {t("stock.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
