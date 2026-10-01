// True for values like "12", "12.5" or "12.50" with at most `decimals` decimal places.
export function isValidDecimal(value, decimals) {
  const pattern = new RegExp(`^\\d+(\\.\\d{1,${decimals}})?$`);
  return pattern.test(String(value).trim());
}
