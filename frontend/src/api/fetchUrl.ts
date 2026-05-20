/**
 * api/fetchUrl.ts
 * ---------------
 * Client for POST /api/fetch-url
 */

export interface UrlFetchResult {
  url: string;
  title: string;
  text: string;
  char_count: number;
  domain: string;
}

export interface UrlFetchError {
  detail: string;
}

/**
 * Fetches a public article URL and returns extracted clean text.
 * Throws a plain Error with a user-readable message on failure.
 */
export async function fetchUrlContent(url: string): Promise<UrlFetchResult> {
  const response = await fetch("/api/fetch-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  const data = await response.json();

  if (!response.ok) {
    // FastAPI returns { detail: "..." } for all DistillError raises
    const err = data as UrlFetchError;
    throw new Error(err.detail ?? "Failed to fetch URL. Please try again.");
  }

  return data as UrlFetchResult;
}
