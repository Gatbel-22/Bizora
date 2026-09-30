import { Outlet } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";
import FullPageMessage from "./ui/FullPageMessage";

export default function RequireRole({ roles }) {
  const { role } = useAuth();
  if (!roles.includes(role)) {
    return (
      <FullPageMessage
        fullScreen={false}
        title={t("error.forbidden.title")}
        message={t("error.forbidden.message")}
      />
    );
  }
  return <Outlet />;
}
