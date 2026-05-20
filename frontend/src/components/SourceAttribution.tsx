/**
 * components/results/SourceAttribution.tsx
 * -----------------------------------------
 * Shown at the top of ResultsPage when the session was created from a URL.
 * Displays the article title and a "Read original" link back to the source.
 */

import React from "react";
import {
  Box,
  Link,
  SpaceBetween,
  Badge,
} from "@cloudscape-design/components";

interface SourceAttributionProps {
  sourceUrl: string;
  title?: string;
  domain?: string;
}

export const SourceAttribution: React.FC<SourceAttributionProps> = ({
  sourceUrl,
  title,
  domain,
}) => {
  const displayDomain =
    domain ?? new URL(sourceUrl).hostname.replace(/^www\./, "");

  return (
    <Box
      padding="s"
      borderRadius="s"
      // Subtle info banner
      background="awsui-color-background-status-info"
    >
      <SpaceBetween size="xxs" direction="horizontal" alignItems="center">
        <Badge color="blue">📰 Article</Badge>

        <SpaceBetween size="xxs" direction="vertical">
          {title && (
            <Box variant="strong" fontSize="body-m">
              {title}
            </Box>
          )}
          <Link href={sourceUrl} external>
            Read original on {displayDomain}
          </Link>
        </SpaceBetween>
      </SpaceBetween>
    </Box>
  );
};

export default SourceAttribution;


/*
 * ── How to use in ResultsPage.tsx ─────────────────────────────────────────
 *
 * import { SourceAttribution } from "../components/results/SourceAttribution";
 *
 * // Inside your ResultsPage JSX, before the score cards:
 * {session.source_url && (
 *   <SourceAttribution
 *     sourceUrl={session.source_url}
 *     title={session.title}
 *   />
 * )}
 */
