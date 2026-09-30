import { Navigate, Outlet, useLocation } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";
import Button from "./ui/Button";
import FullPageMessage from "./ui/FullPageMessage";
import PageLoader from "./ui/PageLoader";

export default function ProtectedRoute() {
  const { status, activeMembership, retry, logout } = useAuth();
  const location = useLocation();

  if (status === "loading") return <PageLoader />;

  if (status === "error") {
    return (
      <FullPageMessage title={t("error.connection.title")} message={t("error.network")}>
        <Button onClick={retry}>{t("common.tryAgain")}</Button>
      </FullPageMessage>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!activeMembership) {
    return (
      <FullPageMessage title={t("error.noBusiness.title")} message={t("error.noBusiness.message")}>
        <Button variant="secondary" onClick={logout}>
          {t("common.signOut")}
        </Button>
      </FullPageMessage>
    );
  }

  return <Outlet />;
}
