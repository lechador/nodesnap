export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      result.error?.message ?? result.detail?.message ?? result.detail;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status}). Please try again.`,
    );
  }
  return result.data as T;
}
export function mutationOptions(
  base: string,
  body: Record<string, unknown>,
): RequestInit {
  return {
    method: "POST",
    headers: {
      "If-Match": `"${base}"`,
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({ base_revision_id: base, ...body }),
  };
}
