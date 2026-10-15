import { t } from "../i18n";
import { formatDateTime, formatMoney, formatQuantity } from "./format";

export function buildReceiptText(receipt) {
  const money = (value) => formatMoney(value, receipt.business.currency);
  const lines = [receipt.business.name];
  if (receipt.business.address) lines.push(receipt.business.address);
  if (receipt.business.phone) lines.push(receipt.business.phone);

  lines.push("", t("receipt.number", { number: receipt.number }), formatDateTime(receipt.sold_at));
  if (receipt.served_by) lines.push(t("receipt.servedBy", { name: receipt.served_by }));
  if (receipt.customer) lines.push(t("receipt.customer", { name: receipt.customer }));

  lines.push("");
  for (const item of receipt.items) {
    lines.push(
      item.name,
      `  ${formatQuantity(item.quantity)} x ${money(item.unit_price)} = ${money(item.line_total)}`
    );
  }

  lines.push("");
  if (Number(receipt.discount) > 0) {
    lines.push(
      `${t("receipt.subtotal")}: ${money(receipt.subtotal)}`,
      `${t("receipt.discount")}: -${money(receipt.discount)}`
    );
  }
  lines.push(
    `${t("receipt.total")}: ${money(receipt.total)}`,
    `${t("receipt.paid")}: ${money(receipt.amount_paid)}`
  );
  if (Number(receipt.outstanding_amount) > 0) {
    lines.push(`${t("receipt.balance")}: ${money(receipt.outstanding_amount)}`);
  }
  lines.push("", t("receipt.thanks"));
  return lines.join("\n");
}
