const STYLES = {
  error: { box: "border-red-300 bg-red-50 text-red-900", label: "Error" },
  success: { box: "border-green-300 bg-green-50 text-green-900", label: "Success" },
  info: { box: "border-sky-300 bg-sky-50 text-sky-900", label: "Note" },
};

export default function Alert({ variant = "error", children, className = "" }) {
  const style = STYLES[variant];
  return (
    <div
      role={variant === "error" ? "alert" : "status"}
      className={`rounded-lg border px-4 py-3 text-sm ${style.box} ${className}`}
    >
      <span className="font-semibold">{style.label}: </span>
      {children}
    </div>
  );
}
