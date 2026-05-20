import { useState } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Toggle from "@cloudscape-design/components/toggle";
import Textarea from "@cloudscape-design/components/textarea";
import Button from "@cloudscape-design/components/button";
import Alert from "@cloudscape-design/components/alert";
import Box from "@cloudscape-design/components/box";
import ExpandableSection from "@cloudscape-design/components/expandable-section";
import Spinner from "@cloudscape-design/components/spinner";
import { evaluateVoice } from "../../api/evaluate";
import type { Question, VoiceResult } from "../../types";
import VoiceRecorder from "./VoiceRecorder";
import DifficultyBadge from "./DifficultyBadge";

interface Props {
  question: Question;
  sessionId: string;
  onAnswered: (result: VoiceResult) => void;
  onNext: () => void;
}

export default function TeachItBack({ question, sessionId, onAnswered, onNext }: Props) {
  const [useVoice, setUseVoice] = useState(true);
  const [textAnswer, setTextAnswer] = useState("");
  const [result, setResult] = useState<VoiceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wordCount = (s: string) =>
    s.trim().split(/\s+/).filter(Boolean).length;

  const submitAnswer = async (answer: string, wasVoice: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const r = await evaluateVoice({
        session_id: sessionId,
        question_id: question.id,
        student_answer: answer,
        was_voice: wasVoice,
      });
      setResult(r);
      onAnswered(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          description={
            <SpaceBetween direction="horizontal" size="xs">
              <Box color="text-body-secondary">{question.topic}</Box>
              <DifficultyBadge difficulty={question.difficulty} />
            </SpaceBetween>
          }
        >
          {question.question}
        </Header>
      }
    >
      <SpaceBetween size="m">
        {/* Optional rubric hint */}
        {question.evaluation_rubric && (
          <ExpandableSection headerText="What makes a strong answer?">
            <Box color="text-body-secondary">{question.evaluation_rubric}</Box>
          </ExpandableSection>
        )}

        {/* Answer input — hidden once result is received */}
        {!result && (
          <>
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
              <Box>Answer by:</Box>
              <Toggle
                checked={useVoice}
                onChange={({ detail }) => setUseVoice(detail.checked)}
              >
                {useVoice ? "Voice" : "Text"}
              </Toggle>
            </SpaceBetween>

            {useVoice ? (
              <VoiceRecorder
                maxSeconds={120}
                onTranscriptReady={(t) => submitAnswer(t, true)}
                onError={(msg) => {
                  // Auto-fallback to text mode when mic is unavailable
                  setUseVoice(false);
                  setError(msg);
                }}
              />
            ) : (
              <SpaceBetween size="s">
                <Textarea
                  value={textAnswer}
                  onChange={({ detail }) => setTextAnswer(detail.value)}
                  placeholder="Explain the concept in your own words..."
                  rows={8}
                />
                <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                  <Box color="text-body-secondary" fontSize="body-s">
                    {wordCount(textAnswer)} words (minimum 20 recommended)
                  </Box>
                  <Button
                    variant="primary"
                    onClick={() => submitAnswer(textAnswer, false)}
                    disabled={loading || wordCount(textAnswer) < 5}
                    loading={loading}
                  >
                    {loading ? <Spinner /> : "Submit Answer"}
                  </Button>
                </SpaceBetween>
              </SpaceBetween>
            )}
          </>
        )}

        {error && <Alert type="error">{error}</Alert>}

        {/* Post-evaluation result */}
        {result && (
          <SpaceBetween size="m">
            {/* Verdict + score */}
            <Alert
              type={result.verdict_type as "success" | "info" | "warning" | "error"}
              header={`${result.verdict} — Score: ${result.weighted_score.toFixed(1)} / 5.0`}
            >
              {/* Dimension breakdown */}
              <SpaceBetween size="xxs">
                {result.dimension_scores.map((d) => (
                  <Box key={d.key} fontSize="body-s">
                    {d.label}: {d.score} / 5
                  </Box>
                ))}
              </SpaceBetween>
            </Alert>

            {/* Why you got this score */}
            {result.narrative_debrief && (
              <Alert type="info" header="Feedback on your answer">
                {result.narrative_debrief.split("\n\n").map((para, i) => (
                  <Box key={i} margin={{ bottom: "xs" }}>
                    {para}
                  </Box>
                ))}
              </Alert>
            )}

            {/* What to study */}
            {result.study_recommendations.length > 0 && (
              <Alert type="warning" header="What to review">
                <ul style={{ margin: 0, paddingLeft: "1.2em" }}>
                  {result.study_recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </Alert>
            )}

            {/* Follow-up question if provided */}
            {result.follow_up_question && (
              <Alert type="info" header="Think about this">
                {result.follow_up_question}
              </Alert>
            )}

            <Box float="right">
              <Button
                variant="primary"
                onClick={onNext}
                iconAlign="right"
                iconName="angle-right"
              >
                Next Question
              </Button>
            </Box>
          </SpaceBetween>
        )}
      </SpaceBetween>
    </Container>
  );
}
