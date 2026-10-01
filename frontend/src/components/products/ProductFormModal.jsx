import { useState } from "react";
import { createProduct, updateProduct } from "../../api/inventory";
import { UNITS } from "../../config/options";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import { isValidDecimal } from "../../utils/validation";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import SelectField from "../ui/SelectField";
import TextField from "../ui/TextField";

const EMPTY_FORM = {
  name: "",
  sku: "",
  category: "",
  unit: "PIECE",
  selling_price: "",
  purchase_price: "",
  min_stock_threshold: "",
  opening_stock: "",
  description: "",
  is_active: true,
};

function toForm(product) {
  return {
    name: product.name,
    sku: product.sku ?? "",
    category: product.category ?? "",
    unit: product.unit,
    selling_price: product.selling_price,
    purchase_price: product.purchase_price ?? "",
    min_stock_threshold: String(Number(product.min_stock_threshold)),
    opening_stock: "",
    description: product.description ?? "",
    is_active: product.is_active,
  };
}

function validate(form, isEdit) {
  const errors = {};
  if (!form.name.trim()) errors.name = t("validation.required");
  if (!isValidDecimal(form.selling_price, 2)) errors.selling_price = t("validation.amount");
  if (form.purchase_price.trim() && !isValidDecimal(form.purchase_price, 2)) {
    errors.purchase_price = t("validation.amount");
  }
  if (form.min_stock_threshold.trim() && !isValidDecimal(form.min_stock_threshold, 3)) {
    errors.min_stock_threshold = t("validation.quantity");
  }
  if (!isEdit && form.opening_stock.trim() && !isValidDecimal(form.opening_stock, 3)) {
    errors.opening_stock = t("validation.quantity");
  }
  return errors;
}

export default function ProductFormModal({ product, categories, onClose, onSaved }) {
  const isEdit = Boolean(product);
  const [form, setForm] = useState(isEdit ? toForm(product) : EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = validate(form, isEdit);
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    const payload = {
      name: form.name.trim(),
      sku: form.sku.trim(),
      category: form.category || null,
      unit: form.unit,
      selling_price: form.selling_price.trim(),
      purchase_price: form.purchase_price.trim() || "0",
      min_stock_threshold: form.min_stock_threshold.trim() || "0",
      description: form.description.trim(),
    };
    if (isEdit) payload.is_active = form.is_active;
    else payload.opening_stock = form.opening_stock.trim() || "0";

    setSubmitting(true);
    try {
      if (isEdit) await updateProduct(product.id, payload);
      else await createProduct(payload);
      onSaved(t("products.saved"));
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  const categoryOptions = [
    { value: "", label: t("field.noCategory") },
    ...categories.map((category) => ({ value: category.id, label: category.name })),
  ];

  return (
    <Modal
      title={isEdit ? t("productForm.editTitle") : t("productForm.addTitle")}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("field.productName")}
          name="name"
          required
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("field.sku")}
            name="sku"
            value={form.sku}
            onChange={handleChange}
            error={fieldErrors.sku}
          />
          <SelectField
            label={t("field.unit")}
            name="unit"
            options={UNITS}
            value={form.unit}
            onChange={handleChange}
            error={fieldErrors.unit}
          />
        </div>
        <SelectField
          label={t("field.category")}
          name="category"
          options={categoryOptions}
          value={form.category}
          onChange={handleChange}
          error={fieldErrors.category}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("field.sellingPrice")}
            name="selling_price"
            inputMode="decimal"
            required
            value={form.selling_price}
            onChange={handleChange}
            error={fieldErrors.selling_price}
          />
          <TextField
            label={t("field.purchasePrice")}
            name="purchase_price"
            inputMode="decimal"
            value={form.purchase_price}
            onChange={handleChange}
            error={fieldErrors.purchase_price}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={t("field.minStock")}
            name="min_stock_threshold"
            inputMode="decimal"
            hint={t("field.minStockHint")}
            value={form.min_stock_threshold}
            onChange={handleChange}
            error={fieldErrors.min_stock_threshold}
          />
          {!isEdit && (
            <TextField
              label={t("field.openingStock")}
              name="opening_stock"
              inputMode="decimal"
              hint={t("field.openingStockHint")}
              value={form.opening_stock}
              onChange={handleChange}
              error={fieldErrors.opening_stock}
            />
          )}
        </div>
        <div>
          <label htmlFor="product-description" className="block text-sm font-medium text-slate-800">
            {t("field.description")}
          </label>
          <textarea
            id="product-description"
            name="description"
            rows={2}
            value={form.description}
            onChange={handleChange}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900"
          />
        </div>
        {isEdit && (
          <label className="flex min-h-11 items-center gap-3 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
              className="h-5 w-5"
            />
            {t("field.isActive")}
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
