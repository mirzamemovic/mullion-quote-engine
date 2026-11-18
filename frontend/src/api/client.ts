/**
 * The one way the app talks to the API: same origin, the session cookie, and the CSRF header
 * on every unsafe request (PLAN.md section 9). Errors arrive as RFC 9457 problem JSON.
 */
import type { components } from "./schema";

export type Schemas = components["schemas"];

export const API_BASE = "/api/v1";
const CSRF_COOKIE = "__Host-csrf";
const CSRF_HEADER = "X-CSRF-Token";

export interface FieldError {
  field: string;
  message: string;
}

/** One problem in an uploaded file: the row a spreadsheet shows (header = 1) and the column. */
export interface FileProblem {
  row: number;
  column: string;
  message: string;
}

/** A failed request, carrying the server's problem details. */
export class ApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly errors: FieldError[];
  /** CSV imports: every problem found, with its row and column. */
  readonly problems: FileProblem[];
  /** A missing catalogue value: its name, such as ``deductions.sash_width``. */
  readonly constant: string | undefined;

  constructor(status: number, body: unknown) {
    const problem = (body ?? {}) as {
      title?: unknown;
      detail?: unknown;
      errors?: unknown;
      problems?: unknown;
      constant?: unknown;
    };
    const detail = typeof problem.detail === "string" ? problem.detail : `HTTP ${status}`;
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.title = typeof problem.title === "string" ? problem.title : "error";
    this.errors = Array.isArray(problem.errors) ? (problem.errors as FieldError[]) : [];
    this.problems = Array.isArray(problem.problems) ? (problem.problems as FileProblem[]) : [];
    this.constant = typeof problem.constant === "string" ? problem.constant : undefined;
  }
}

/** A step-up refusal: the action needs the password again. */
export function needsReauth(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403 && /password/i.test(error.message);
}

/** The address of a file the API serves (CSV), for a plain download link on the same origin. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** A file's bytes as base64, for JSON uploads (the server works out the encoding). */
export async function fileBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

export function csrfToken(cookies: string = document.cookie): string | undefined {
  for (const part of cookies.split(";")) {
    const [name, ...value] = part.trim().split("=");
    if (name === CSRF_COOKIE) {
      return decodeURIComponent(value.join("="));
    }
  }
  return undefined;
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET") {
    const token = csrfToken();
    if (token !== undefined) {
      headers[CSRF_HEADER] = token;
    }
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data as T;
}

export const get = <T>(path: string) => request<T>("GET", path);
export const post = <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {});
export const put = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
export const patch = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
export const del = <T>(path: string) => request<T>("DELETE", path);
