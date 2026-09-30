import { Link } from "react-router-dom";
import FullPageMessage from "../components/ui/FullPageMessage";
import { t } from "../i18n";

export default function NotFoundPage() {
  return (
    <FullPageMessage
      fullScreen={false}
      title={t("error.notFound.title")}
      message={t("error.notFound.message")}
    >
      <Link to="/" className="font-semibold text-brand-700 underline">
        {t("error.notFound.home")}
      </Link>
    </FullPageMessage>
  );
}
