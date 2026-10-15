import { isValidDecimal } from "./validation";

export const round2 = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
const round3 = (value) => Math.round((value + Number.EPSILON) * 1000) / 1000;

export function addToCart(cart, product) {
  const existing = cart.find((line) => line.productId === product.id);
  if (existing) {
    return cart.map((line) =>
      line.productId === product.id
        ? { ...line, quantity: String(round3(Number(line.quantity) + 1)) }
        : line
    );
  }
  return [
    ...cart,
    {
      productId: product.id,
      name: product.name,
      sku: product.sku ?? "",
      unit: product.unit,
      unitPrice: product.selling_price,
      stock: product.current_stock,
      quantity: "1",
    },
  ];
}

export function setQuantity(cart, productId, quantity) {
  return cart.map((line) => (line.productId === productId ? { ...line, quantity } : line));
}

// Plus/minus buttons. Going to zero removes the line.
export function stepQuantity(cart, productId, delta) {
  return cart.flatMap((line) => {
    if (line.productId !== productId) return [line];
    const next = round3(Number(line.quantity) + delta);
    return next > 0 ? [{ ...line, quantity: String(next) }] : [];
  });
}

export const removeLine = (cart, productId) => cart.filter((line) => line.productId !== productId);

export function isLineValid(line) {
  return isValidDecimal(line.quantity, 3) && Number(line.quantity) > 0;
}

export function lineTotal(line) {
  if (!isLineValid(line)) return 0;
  return round2(Number(line.quantity) * Number(line.unitPrice));
}

export function cartSubtotal(cart) {
  return round2(cart.reduce((sum, line) => sum + lineTotal(line), 0));
}

export function exceedsStock(line) {
  return isLineValid(line) && Number(line.quantity) > Number(line.stock);
}

export function saleTotals(cart, discount) {
  const subtotal = cartSubtotal(cart);
  const discountAmount = isValidDecimal(discount ?? "", 2) ? Number(discount) : 0;
  return { subtotal, discount: discountAmount, total: round2(subtotal - discountAmount) };
}

export function buildSalePayload({
  cart,
  customerId,
  discount,
  paymentMethod,
  amountPaid,
  dueDate,
  note,
  clientReference,
}) {
  const payload = {
    items: cart.map((line) => ({ product: line.productId, quantity: line.quantity.trim() })),
    payment_method: paymentMethod,
  };
  if (customerId) payload.customer = customerId;
  if (isValidDecimal(discount ?? "", 2) && Number(discount) > 0) payload.discount = discount.trim();
  if (paymentMethod !== "CREDIT" && amountPaid) payload.amount_paid = amountPaid;
  if (dueDate) payload.due_date = dueDate;
  if (note && note.trim()) payload.note = note.trim();
  if (clientReference) payload.client_reference = clientReference;
  return payload;
}
