import { useState } from "react";
import {
  createExpenseCategory,
  deleteExpenseCategory,
  listExpenseCategories,
  updateExpenseCategory,
} from "../../api/expenses";
import useFetch from "../../hooks/useFetch";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import Spinner from "../ui/Spinner";
import TextField from "../ui/TextField";

export default function ExpenseCategoriesModal({ onClose, onChanged }) {
  const list = useFetch(() => listExpenseCategories(), "expense-categories-modal");
  const [editing, setEditing] = useState(null);
  const [name, setName] = useState("");
  const [affectsProfit, setAffectsProfit] = useState(true);
  const [nameError, setNameError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmId, setConfirmId] = useState(null);

  const resetForm = () => {
    setEditing(null);
    setName("");
    setAffectsProfit(true);
    setNameError("");
  };

  const startEdit = (category) => {
    setEditing(category);
    setName(category.name);
    setAffectsProfit(category.affects_profit);
    setNameError("");
    setMessage("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setNameError("");
    setMessage("");
    if (!name.trim()) {
      setNameError(t("validation.required"));
      return;
    }
    const payload = { name: name.trim(), affects_profit: affectsProfit };
    setBusy(true);
    try {
      if (editing) await updateExpenseCategory(editing.id, payload);
      else await createExpenseCategory(payload);
      resetForm();
      list.reload();
      onChanged();
    } catch (error) {
      const fields = getFieldErrors(error);
      if (fields.name) setNameError(fields.name);
      else setMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (category) => {
    setMessage("");
    setBusy(true);
    try {
      await deleteExpenseCategory(category.id);
      if (editing?.id === category.id) resetForm();
      list.reload();
      onChanged();
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setConfirmId(null);
      setBusy(false);
    }
  };

  const categories = list.data?.results ?? [];

  return (
    <Modal title={t("expenseCategories.title")} onClose={onClose}>
      <form onSubmit={handleSubmit} noValidate className="space-y-3">
        <TextField
          label={t("expenseCategories.name")}
          name="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={nameError}
        />
        <div>
          <label className="flex min-h-11 items-center gap-3 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={affectsProfit}
              onChange={(event) => setAffectsProfit(event.target.checked)}
              className="h-5 w-5"
            />
            {t("expenseCategories.affectsProfit")}
          </label>
          <p className="text-sm text-slate-600">{t("expenseCategories.affectsProfitHint")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" loading={busy}>
            {editing ? t("expenseCategories.saveChanges") : t("expenseCategories.add")}
          </Button>
          {editing && (
            <Button variant="secondary" onClick={resetForm}>
              {t("expenseCategories.cancelEdit")}
            </Button>
          )}
        </div>
      </form>

      {message && <Alert className="mt-4">{message}</Alert>}

      <div className="mt-4">
        {list.loading && !list.data && (
          <div role="status" className="flex justify-center py-6 text-brand-700">
            <Spinner className="h-6 w-6" />
          </div>
        )}
        {list.error && (
          <Alert>
            {t("expenseCategories.loadError")} {getErrorMessage(list.error)}{" "}
            <button type="button" onClick={list.reload} className="font-semibold underline">
              {t("common.tryAgain")}
            </button>
          </Alert>
        )}
        {list.data && categories.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-600">{t("expenseCategories.empty")}</p>
        )}
        <ul>
          {categories.map((category) => (
            <li
              key={category.id}
              className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 py-2 last:border-b-0"
            >
              <div>
                <p className="font-medium text-slate-900">{category.name}</p>
                <p className="text-xs text-slate-600">
                  {t("expenseCategories.expenses", { count: category.expense_count })}
                  {!category.affects_profit && ` · ${t("expenses.notInProfit")}`}
                </p>
              </div>
              {confirmId === category.id ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-slate-800">
                    {t("expenseCategories.confirm", { name: category.name })}
                  </span>
                  <Button variant="secondary" onClick={() => setConfirmId(null)}>
                    {t("expenses.keep")}
                  </Button>
                  <Button loading={busy} onClick={() => handleDelete(category)}>
                    {t("expenses.confirmYes")}
                  </Button>
                </div>
              ) : (
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    onClick={() => startEdit(category)}
                    aria-label={`${t("expenseCategories.edit")}: ${category.name}`}
                  >
                    {t("expenseCategories.edit")}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setConfirmId(category.id)}
                    aria-label={`${t("common.delete")}: ${category.name}`}
                  >
                    {t("common.delete")}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  );
}
