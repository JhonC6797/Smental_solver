import { useCallback, useEffect, useRef, useState } from "react";

import { Board } from "./board/Board";
import { COLOR } from "./board/theme";
import { Log } from "./ui/Log";
import { ProgressChart } from "./ui/ProgressChart";
import { Rail } from "./ui/Rail";
import { useNarrow } from "./ui/useNarrow";
import {
  CLOSED,
  LIVE_SOLVER,
  hasSession,
  loadRecording,
  rejoinSolve,
  startSolve,
  type Connection,
  type Guess,
  type Message,
} from "./api";

/** Fast enough to watch the shape of the search, slow enough to follow. */
const REPLAY_STEP_MS = 170;
const LOG_WIDTH = 224;
const RAIL_HEIGHT = 68;

export default function App() {
  const [guesses, setGuesses] = useState<Guess[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [hypothesis, setHypothesis] = useState<[number, number, number] | null>(
    null,
  );
  const [note, setNote] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [logOpen, setLogOpen] = useState(false);
  const [chartOpen, setChartOpen] = useState(false);
  const [recordsOnly, setRecordsOnly] = useState(false);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [replayIndex, setReplayIndex] = useState<number | null>(null);
  const [pendingPlayback, setPendingPlayback] = useState(false);
  const [recordedAt, setRecordedAt] = useState<string | null>(null);

  const startedAt = useRef<number | null>(null);
  const connection = useRef<Connection>(CLOSED);
  const narrow = useNarrow();
  const replaying = replayIndex !== null;

  const handle = useCallback((message: Message) => {
    switch (message.type) {
      case "run_started":
        // Taken from the server, so a rejoined run shows its real age.
        startedAt.current = Date.parse(message.started_at);
        setRunning(true);
        break;
      case "guess":
        setGuesses((previous) => [...previous, message]);
        break;
      case "diagnostics": {
        // Rendered by value type, never by key name, so a different search
        // algorithm can report different internals without a change here.
        const bearing = message.directions["target_estimate"];
        if (bearing) setHypothesis(bearing);
        break;
      }
      case "solved":
        setAnswer(message.word);
        setHypothesis(null); // the guess about where to look is spent
        setNote(`נמצא ב־${message.total_guesses} ניחושים`);
        setElapsed(message.elapsed_seconds);
        setRunning(false);
        break;
      case "failed":
        setNote(message.reason);
        setRunning(false);
        break;
    }
  }, []);

  const lose = useCallback((reason: string) => {
    setNote(reason);
    setRunning(false);
  }, []);

  // Rejoin the run this tab was watching before it reloaded. The server
  // replays what was missed, so nothing is lost.
  useEffect(() => {
    if (!LIVE_SOLVER || !hasSession()) return;
    const rejoined = rejoinSolve({ onMessage: handle, onLost: lose });
    if (rejoined) connection.current = rejoined;
    return () => {
      connection.current.close();
      connection.current = CLOSED;
    };
  }, [handle, lose]);

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      if (startedAt.current) setElapsed((Date.now() - startedAt.current) / 1000);
    }, 200);
    return () => clearInterval(timer);
  }, [running]);

  // The recording lands in one burst; start playing it once it is all here.
  useEffect(() => {
    if (!pendingPlayback || !answer) return;
    setPendingPlayback(false);
    setReplayIndex(0);
  }, [pendingPlayback, answer]);

  useEffect(() => {
    if (replayIndex === null) return;
    if (replayIndex >= guesses.length) {
      setReplayIndex(null);
      return;
    }
    const timer = setTimeout(() => setReplayIndex(replayIndex + 1), REPLAY_STEP_MS);
    return () => clearTimeout(timer);
  }, [replayIndex, guesses.length]);

  function clearBoard() {
    connection.current.close();
    connection.current = CLOSED;
    setGuesses([]);
    setAnswer(null);
    setHypothesis(null);
    setNote(null);
    setElapsed(0);
    setReplayIndex(null);
    setPendingPlayback(false);
    setHighlighted(null);
    startedAt.current = Date.now();
  }

  async function solve() {
    clearBoard();
    setRunning(true);
    // A recording arrives all at once, so it is played back rather than
    // dumped: the point of the board is watching the search happen.
    if (!LIVE_SOLVER) {
      const recording = await loadRecording();
      if (recording === null) {
        setNote("עוד לא פורסמה ריצה. המשימה היומית מפרסמת אותה כמה פעמים ביום.");
        setRunning(false);
        return;
      }
      setRecordedAt(recording.recorded_at);
      recording.events.forEach(handle);
      setPendingPlayback(true);
      return;
    }

    try {
      const joined = await startSolve({ onMessage: handle, onLost: lose });
      connection.current = joined.connection;
      if (joined.recorded) setPendingPlayback(true);
    } catch {
      setNote("אין קשר לשרת. הפעילו אותו עם python -m uvicorn server.app:app");
      setRunning(false);
    }
  }

  function replay() {
    setRecordsOnly(false);
    setHighlighted(null);
    setReplayIndex(0);
  }

  // During a replay the board is rewound: it holds only the guesses made so
  // far, and the answer stays hidden until the last one lands.
  const visible = replaying ? guesses.slice(0, replayIndex) : guesses;
  const visibleAnswer = replaying ? null : answer;

  const best = visible.reduce<Guess | null>(
    (top, guess) => (top === null || guess.similarity > top.similarity ? guess : top),
    null,
  );

  return (
    <main
      /* The overlay that drei positions over the canvas resolves its offsets
         against the container's direction, so the board's layer stays LTR and
         each piece of Hebrew chrome declares RTL for itself. */
      dir="ltr"
      style={{
        position: "fixed",
        inset: 0,
        background: COLOR.field,
        overflow: "hidden",
      }}
    >
      <Board
        guesses={visible}
        answer={visibleAnswer}
        hypothesis={hypothesis}
        recordsOnly={recordsOnly}
        highlighted={highlighted}
        onHighlight={setHighlighted}
      />

      {guesses.length === 0 && !running && <Opening />}

      {recordedAt && guesses.length > 0 && <RecordedOn at={recordedAt} />}

      {logOpen && guesses.length > 0 && (
        <Log
          guesses={visible}
          narrow={narrow}
          recordsOnly={recordsOnly}
          highlighted={highlighted}
          onFilter={setRecordsOnly}
          onHighlight={setHighlighted}
          onClose={() => setLogOpen(false)}
        />
      )}

      {chartOpen && guesses.length > 0 && (
        <section
          dir="rtl"
          aria-label="גרף ההתקדמות"
          style={{
            position: "absolute",
            left: logOpen && !narrow ? LOG_WIDTH : 0,
            right: 0,
            bottom: RAIL_HEIGHT,
            zIndex: 25,
            borderTop: `1px solid ${COLOR.rule}`,
            background: `${COLOR.field}f2`,
            backdropFilter: "blur(3px)",
            padding: "4px 16px 0",
          }}
        >
          <ProgressChart
            guesses={visible}
            highlighted={highlighted}
            onHighlight={setHighlighted}
          />
        </section>
      )}

      <Rail
        running={running}
        replaying={replaying}
        solved={answer !== null && !replaying}
        best={best?.word ?? null}
        bestScore={best?.similarity ?? 0}
        count={visible.length}
        elapsed={elapsed}
        note={replaying ? null : note}
        narrow={narrow}
        logOpen={logOpen}
        chartOpen={chartOpen}
        canReplay={!running && guesses.length > 1}
        onToggleLog={() => setLogOpen((open) => !open)}
        onToggleChart={() => setChartOpen((open) => !open)}
        onReplay={replay}
        onSolve={solve}
      />
    </main>
  );
}

/** The board starts empty, so the empty state says what the board is for. */
function Opening() {
  return (
    <div
      dir="rtl"
      style={{
        position: "absolute",
        insetInlineStart: 0,
        insetInlineEnd: 0,
        top: 40,
        zIndex: 5,
        textAlign: "center",
        pointerEvents: "none",
        padding: "0 24px",
      }}
    >
      <h1
        style={{
          margin: 0,
          fontFamily: "'Frank Ruhl Libre', Georgia, serif",
          fontWeight: 400,
          fontSize: "clamp(1.6rem, 4vw, 2.4rem)",
          color: COLOR.ink,
        }}
      >
        מציאת המילה היומית בסמענטל
      </h1>
      <p
        style={{
          margin: "10px auto 0",
          maxWidth: "46ch",
          fontSize: 15,
          lineHeight: 1.65,
          color: COLOR.inkSoft,
        }}
      >
        מילה אחת מוסתרת במרכז. כל ניחוש נוחת במרחק שנקבע מהציון שהמשחק החזיר,
        ובכיוון שנקבע ממשמעותו, עד שהחיפוש סוגר על התשובה.
      </p>
    </div>
  );
}

/**
 * When the run was solved. The page shows a recording, so saying when it
 * was made is the difference between a stale board and an honest one.
 */
function RecordedOn({ at }: { at: string }) {
  const when = new Date(at);
  if (Number.isNaN(when.getTime())) return null;
  return (
    <p
      dir="rtl"
      style={{
        position: "absolute",
        top: 14,
        insetInlineStart: 0,
        insetInlineEnd: 0,
        margin: 0,
        zIndex: 5,
        textAlign: "center",
        fontSize: 12,
        color: COLOR.inkFaint,
        pointerEvents: "none",
      }}
    >
      נפתר ב־{when.toLocaleString("he-IL", { dateStyle: "short", timeStyle: "short" })}
    </p>
  );
}
