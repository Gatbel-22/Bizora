import { t } from "../../i18n";
import Spinner from "./Spinner";

export default function PageLoader() {
  return (
    <div
      role="status"
      className="flex min-h-screen items-center justify-center gap-3 text-slate-600"
    >
      <Spinner className="h-6 w-6 text-brand-700" />
      <span>{t("common.loading")}</span>
    </div>
  );
}
