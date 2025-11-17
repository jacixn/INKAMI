const defaultApiBase =
  process.env.NODE_ENV === "production"
    ? "https://inkami-api.fly.dev"
    : "http://localhost:8000";

export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? defaultApiBase;

export async function fetcher(path: string, init?: RequestInit) {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || "API error");
  }

  return response.json();
}

