import EmptyState from "../components/ui/EmptyState";
import PageHeader from "../components/ui/PageHeader";
import { t } from "../i18n";

export default function ComingSoonPage({ titleKey }) {
  return (
    <>
      <PageHeader title={t(titleKey)} />
      <EmptyState title={t("comingSoon.title")} message={t("comingSoon.message")} />
    </>
  );
}
