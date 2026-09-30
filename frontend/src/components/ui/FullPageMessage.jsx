export default function FullPageMessage({ title, message, children, fullScreen = true }) {
  return (
    <div
      className={`flex flex-col items-center justify-center px-6 text-center ${
        fullScreen ? "min-h-screen" : "py-16"
      }`}
    >
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 max-w-md text-slate-600">{message}</p>
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}
