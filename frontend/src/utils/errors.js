// Turns any API/network error into a message a business owner can understand.
// We'll extend this once the backend's standard error format exists.
export function getErrorMessage(error) {
  if (error?.code === "ECONNABORTED") {
    return "The request took too long. Please try again.";
  }
  if (!error?.response) {
    return "Can't reach the server. Check your internet connection and try again.";
  }
  const { status, data } = error.response;
  if (status >= 500) {
    return "Something went wrong on our side. Please try again shortly.";
  }
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  return "Something went wrong. Please try again.";
}
