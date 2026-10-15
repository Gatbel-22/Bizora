import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import CartLine from "../components/sales/CartLine";
import CheckoutModal from "../components/sales/CheckoutModal";
import ProductPicker from "../components/sales/ProductPicker";
import Button from "../components/ui/Button";
import useAuth from "../hooks/useAuth";
import usePersistentState from "../hooks/usePersistentState";
import { t } from "../i18n";
import {
  addToCart,
  cartSubtotal,
  isLineValid,
  removeLine,
  setQuantity,
  stepQuantity,
} from "../utils/cart";
import { formatMoney } from "../utils/format";

export default function NewSalePage() {
  const { business } = useAuth();
  const navigate = useNavigate();
  const currency = business.currency;

  // The cart survives a reload, so a dropped connection or closed tab loses nothing.
  const [cart, setCart] = usePersistentState(`bizora.cart.${business.id}`, []);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const quantities = Object.fromEntries(cart.map((line) => [line.productId, line.quantity]));
  const canCheckout = cart.length > 0 && cart.every(isLineValid);

  const handleDone = (sale) => {
    setCart([]);
    navigate(`/sales/${sale.id}`, { state: { justSold: true } });
  };

  return (
    <div className="pb-28 lg:pb-0">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t("newSale.title")}</h1>
        <Link to="/sales" className="text-sm font-semibold text-brand-700 underline">
          {t("sales.title")}
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <ProductPicker
          onPick={(product) => setCart((current) => addToCart(current, product))}
          quantities={quantities}
        />

        <section aria-labelledby="cart-heading" className="lg:sticky lg:top-6 lg:self-start">
          <div className="mb-2 flex items-center justify-between">
            <h2 id="cart-heading" className="text-lg font-semibold text-slate-900">
              {t("newSale.cart")}
            </h2>
            {cart.length > 0 && (
              <Button
                variant="ghost"
                onClick={() => {
                  if (confirmClear) {
                    setCart([]);
                    setConfirmClear(false);
                  } else {
                    setConfirmClear(true);
                  }
                }}
                onBlur={() => setConfirmClear(false)}
              >
                {confirmClear ? t("newSale.clearConfirm") : t("newSale.clear")}
              </Button>
            )}
          </div>

          {cart.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-600">
              {t("newSale.cartEmpty")}
            </p>
          ) : (
            <ul className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              {cart.map((line) => (
                <CartLine
                  key={line.productId}
                  line={line}
                  currency={currency}
                  onQuantityChange={(id, value) => setCart((c) => setQuantity(c, id, value))}
                  onStep={(id, delta) => setCart((c) => stepQuantity(c, id, delta))}
                  onRemove={(id) => setCart((c) => removeLine(c, id))}
                />
              ))}
            </ul>
          )}

          {/* A sticky bar on phones; sits under the cart on large screens. */}
          <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:static lg:mt-4 lg:border-0 lg:bg-transparent lg:p-0">
            <Button
              className="w-full"
              disabled={!canCheckout}
              onClick={() => setCheckoutOpen(true)}
            >
              {cart.length > 0
                ? t("newSale.charge", { amount: formatMoney(cartSubtotal(cart), currency) })
                : t("newSale.checkout")}
            </Button>
          </div>
        </section>
      </div>

      {checkoutOpen && (
        <CheckoutModal
          cart={cart}
          currency={currency}
          onClose={() => setCheckoutOpen(false)}
          onDone={handleDone}
        />
      )}
    </div>
  );
}
