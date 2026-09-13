export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Kullaniciya gosterilecek tek satirlik hata metni. */
export function errorText(error: unknown): string {
  if (error instanceof ApiError) return `API ${error.status}: ${error.message}`;
  if (error instanceof TypeError) return "API'ye ulaşılamadı";
  return error instanceof Error ? error.message : String(error);
}
