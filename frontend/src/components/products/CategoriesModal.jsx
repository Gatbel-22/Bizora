import { useState } from "react";
import { createCategory, deleteCategory, listCategories } from "../../api/inventory";
import useFetch from "../../hooks/useFetch";
import { t } from "../../i18n";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Modal from "../ui/Modal";
import Spinner from "../ui/Spinner";
import TextField from "../ui/TextField";

export default function CategoriesModal({ onClose, onChanged }) {
  const list = useFetch(() => listCategories(), "categories-modal");
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmId, setConfirmId] = useState(null);

  const handleAdd = async (event) => {
    event.preventDefault();
    setNameError("");
    setMessage("");
    if (!name.trim()) {
      setNameError(t("validation.required"));
      return;
    }
    setBusy(true);
    try {
      await createCategory({ name: name.trim() });
      setName("");
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
      await deleteCategory(category.id);
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
    <Modal title={t("categories.title")} onClose={onClose}>
      <form onSubmit={handleAdd} noValidate className="flex items-start gap-2">
        <TextField
          className="flex-1"
          label={t("categories.name")}
          name="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={nameError}
        />
        <Button type="submit" loading={busy} className="mt-6">
          {t("categories.add")}
        </Button>
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
            {t("categories.loadError")} {getErrorMessage(list.error)}{" "}
            <button type="button" onClick={list.reload} className="font-semibold underline">
              {t("common.tryAgain")}
            </button>
          </Alert>
        )}
        {list.data && categories.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-600">{t("categories.empty")}</p>
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
                  {t("categories.products", { count: category.product_count })}
                </p>
              </div>
              {confirmId === category.id ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-800">
                    {t("categories.confirm", { name: category.name })}
                  </span>
                  <Button variant="secondary" onClick={() => setConfirmId(null)}>
                    {t("categories.keep")}
                  </Button>
                  <Button loading={busy} onClick={() => handleDelete(category)}>
                    {t("categories.confirmYes")}
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  onClick={() => setConfirmId(category.id)}
                  aria-label={`${t("common.delete")}: ${category.name}`}
                >
                  {t("common.delete")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  );
}
