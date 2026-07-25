/** Section 30 API response envelope. */
export interface ApiEnvelope<T> {
  request_id: string;
  data: T;
  errors: string[];
  warnings: string[];
  metadata: {
    contract_version: string;
    generated_at: string;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly errors: string[],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function unwrap<T>(response: Response): Promise<ApiEnvelope<T>> {
  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, [String(response.status)]);
  }
  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (envelope.errors.length > 0) {
    throw new ApiError(envelope.errors.join("; "), envelope.errors);
  }
  return envelope;
}

export async function apiGet<T>(path: string): Promise<ApiEnvelope<T>> {
  return unwrap<T>(await fetch(path));
}

export async function apiPost<T>(path: string, body?: unknown): Promise<ApiEnvelope<T>> {
  return unwrap<T>(
    await fetch(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }),
  );
}
