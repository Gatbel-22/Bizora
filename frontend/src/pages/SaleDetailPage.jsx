import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getReceipt } from "../api/sales";
import CancelSaleModal from "../components/sales/CancelSaleModal";
import Receipt from "../components/sales/Receipt";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import FullPageMessage from "../components/ui/FullPageMessage";
import Spinner from "../components/ui/Spinner";
import { ROLES } from "../config/roles";
import useAuth from "../hooks/useAuth";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { buildReceiptText } from "../utils/receipt";

export default function SaleDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const { role } = useAuth();
  const canCancel = role !== ROLES.STAFF;

  const [cancelling, setCancelling] = useState(false);
  const [notice, setNotice] = useState(location.state?.justSold ? t("receipt.recorded") : "");

  const sale = useFetch(() => getReceipt(id), `receipt-${id}`);

  if (sale.error && !sale.data) {
    const notFound = sale.error.response?.status === 404;
    return (
      <FullPageMessage
        fullScreen={false}
        title={notFound ? t("receipt.notFound") : t("receipt.loadError")}
        message={notFound ? t("receipt.notFoundMessage") : getErrorMessage(sale.error)}
      >
        <div className="flex flex-col items-center gap-3">
          {!notFound && <Button onClick={sale.reload}>{t("common.tryAgain")}</Button>}
          <Link to="/sales" className="font-semibold text-brand-700 underline">
            {t("receipt.back")}
          </Link>
        </div>
      </FullPageMessage>
    );
  }

  if (!sale.data) {
    return (
      <div role="status" className="flex justify-center py-16 text-brand-700">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const receipt = sale.data;

  const handleShare = async () => {
    const text = buildReceiptText(receipt);
    try {
      if (navigator.share) {
        await navigator.share({ title: t("receipt.number", { number: receipt.number }), text });
      } else {
        await navigator.clipboard.writeText(text);
        setNotice(t("receipt.copied"));
      }
    } catch {
      // The person closed the share sheet, or copying isn't allowed. Nothing to do.
    }
  };

  return (
    <>
      <div className="no-print mb-4 flex flex-wrap items-center justify-between gap-3">
        <Link to="/sales" className="text-sm font-semibold text-brand-700 underline">
          {t("receipt.back")}
        </Link>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => window.print()}>
            {t("receipt.print")}
          </Button>
          <Button variant="secondary" onClick={handleShare}>
            {t("receipt.share")}
          </Button>
          <Link
            to="/sales/new"
            className="inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900"
          >
            {t("receipt.newSale")}
          </Link>
        </div>
      </div>

      {notice && (
        <Alert variant="success" className="no-print mx-auto mb-4 max-w-sm">
          {notice}
        </Alert>
      )}

      <Receipt receipt={receipt} />

      {canCancel && receipt.status === "COMPLETED" && (
        <div className="no-print mx-auto mt-6 max-w-sm text-center">
          <Button variant="ghost" onClick={() => setCancelling(true)}>
            {t("receipt.cancelSale")}
          </Button>
        </div>
      )}

      {cancelling && (
        <CancelSaleModal
          sale={{ id: receipt.id, number: receipt.number }}
          onClose={() => setCancelling(false)}
          onCancelled={() => {
            setCancelling(false);
            setNotice(t("receipt.cancelDone"));
            sale.reload();
          }}
        />
      )}
    </>
  );
}
