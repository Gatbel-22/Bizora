import EmptyState from "../components/ui/EmptyState";
import PageHeader from "../components/ui/PageHeader";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";

export default function DashboardPage() {
  const { user, business, role } = useAuth();
  const firstName = user.full_name.trim().split(" ")[0];

  return (
    <>
      <PageHeader
        title={t("dashboard.greeting", { name: firstName })}
        subtitle={`${business.name} · ${t(`role.${role}`)}`}
      />
      <EmptyState title={t("empty.sales.title")} message={t("empty.sales.message")} />
    </>
  );
}
