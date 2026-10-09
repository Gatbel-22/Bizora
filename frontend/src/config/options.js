export const BUSINESS_TYPES = [
  { value: "RETAIL", label: "Retail shop" },
  { value: "SUPERMARKET", label: "Small supermarket" },
  { value: "WHOLESALE", label: "Wholesaler" },
  { value: "PHARMACY", label: "Pharmacy" },
  { value: "RESTAURANT", label: "Restaurant" },
  { value: "SALON", label: "Salon / barbershop" },
  { value: "SERVICE", label: "Service business" },
  { value: "OTHER", label: "Other" },
];

export const CURRENCIES = [
  { value: "SSP", label: "SSP - South Sudanese Pound" },
  { value: "USD", label: "USD - US Dollar" },
  { value: "EUR", label: "EUR - Euro" },
  { value: "KES", label: "KES - Kenyan Shilling" },
  { value: "UGX", label: "UGX - Ugandan Shilling" },
];

export const UNITS = [
  { value: "PIECE", label: "Piece" },
  { value: "PACK", label: "Pack" },
  { value: "BOX", label: "Box" },
  { value: "CARTON", label: "Carton" },
  { value: "BOTTLE", label: "Bottle" },
  { value: "DOZEN", label: "Dozen" },
  { value: "KG", label: "Kilogram" },
  { value: "LITRE", label: "Litre" },
];

export const UNIT_LABELS = Object.fromEntries(
  UNITS.map((unit) => [unit.value, unit.label.toLowerCase()])
);

// Methods that can settle a debt ("credit" is not a payment).
export const PAYMENT_METHODS = ["CASH", "MOBILE_MONEY", "BANK_TRANSFER", "OTHER"];
