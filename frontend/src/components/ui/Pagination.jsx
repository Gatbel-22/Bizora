import { t } from "../../i18n";
import Button from "./Button";

export default function Pagination({ page, pageCount, onPageChange, disabled = false }) {
  if (pageCount <= 1) return null;
  return (
    <nav
      aria-label={t("common.pagination")}
      className="mt-4 flex items-center justify-between gap-3"
    >
      <Button
        variant="secondary"
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        {t("common.previous")}
      </Button>
      <p className="text-sm text-slate-600">{t("common.pageOf", { page, total: pageCount })}</p>
      <Button
        variant="secondary"
        disabled={disabled || page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        {t("common.next")}
      </Button>
    </nav>
  );
}
