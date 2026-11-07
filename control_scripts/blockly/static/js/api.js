// JSON fetch wrapper: throws an Error with the server's message on failure.
export async function jsonRequest(path, options = {}) {
  const requestOptions = {
    ...options
  };
  if (requestOptions.body) {
    requestOptions.headers = {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {})
    };
  }
  const response = await fetch(path, requestOptions);
  let data = {};
  try {
    data = await response.json();
  } catch (_) {}
  if (!response.ok) {
    throw new Error(data.error || "Request failed (" + response.status + ")");
  }
  return data;
}
