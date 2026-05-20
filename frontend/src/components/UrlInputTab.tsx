/**
 * components/UrlInputTab.tsx
 * --------------------------
 * The "Link" tab on InputPage — lets users paste a Medium (or any article) URL
 * and previews the extracted text before analysis.
 */

import React, { useState, useRef } from "react";
import {
  Input,
  Button,
  Alert,
  Box,
  SpaceBetween,
  Textarea,
  Badge,
  Icon,
} from "@cloudscape-design/components";
import { fetchUrlContent, type UrlFetchResult } from "../../api/fetchUrl";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UrlInputTabProps {
  /** Called when text is successfully extracted and user clicks "Use this content" */
  onContentReady: (text: string, sourceUrl: string, title: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const UrlInputTab: React.FC<UrlInputTabProps> = ({ onContentReady }) => {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UrlFetchResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleFetch = async () => {
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await fetchUrlContent(url.trim());
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleFetch();
  };

  const handleUseContent = () => {
    if (!result) return;
    onContentReady(result.text, result.url, result.title);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setUrl("");
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <SpaceBetween size="m">

      {/* URL input row */}
      <Box>
        <SpaceBetween size="xs" direction="horizontal">
          <div style={{ flex: 1 }}>
            <Input
              ref={inputRef}
              value={url}
              onChange={({ detail }) => setUrl(detail.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://medium.com/..."
              type="url"
              disabled={loading || !!result}
              ariaLabel="Article URL"
            />
          </div>
          <Button
            variant="primary"
            onClick={handleFetch}
            loading={loading}
            disabled={!url.trim() || !!result}
            iconName="search"
          >
            {loading ? "Fetching…" : "Fetch Article"}
          </Button>
        </SpaceBetween>

        <Box variant="small" color="text-body-secondary" padding={{ top: "xxs" }}>
          Works with Medium, Substack, dev.to, Hashnode, and most public blogs.
        </Box>
      </Box>

      {/* Error state */}
      {error && (
        <Alert type="error" header="Could not fetch article">
          {error}
        </Alert>
      )}

      {/* Success — preview panel */}
      {result && (
        <SpaceBetween size="m">
          {/* Attribution header */}
          <Box>
            <SpaceBetween size="xs" direction="horizontal" alignItems="center">
              <Badge color="green">✓ Content extracted</Badge>
              <Box variant="small" color="text-body-secondary">
                {result.domain} · {result.char_count.toLocaleString()} characters
              </Box>
            </SpaceBetween>

            {result.title && (
              <Box variant="h3" padding={{ top: "xxs" }}>
                {result.title}
              </Box>
            )}

            <Box variant="small" color="text-body-secondary">
              <a href={result.url} target="_blank" rel="noopener noreferrer">
                {result.url}
              </a>
            </Box>
          </Box>

          {/* Text preview (read-only, scrollable) */}
          <Box>
            <Box variant="small" fontWeight="bold" padding={{ bottom: "xxs" }}>
              Preview (first 1000 characters)
            </Box>
            <Textarea
              value={result.text.slice(0, 1000) + (result.text.length > 1000 ? "\n\n…" : "")}
              readOnly
              rows={8}
              ariaLabel="Extracted content preview"
            />
          </Box>

          {/* Action buttons */}
          <SpaceBetween size="xs" direction="horizontal">
            <Button variant="primary" onClick={handleUseContent} iconName="check">
              Use this content
            </Button>
            <Button variant="link" onClick={handleReset}>
              Try a different URL
            </Button>
          </SpaceBetween>
        </SpaceBetween>
      )}

    </SpaceBetween>
  );
};

export default UrlInputTab;
