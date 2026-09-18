import { useEffect, useRef, useState } from "react";

import { Board } from "./board/Board";
import { COLOR } from "./board/theme";
import { Log } from "./ui/Log";
import { Rail } from "./ui/Rail";
import { useNarrow } from "./ui/useNarrow";
import { startSolve, type Guess, type Message } from "./api";

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
  const startedAt = useRef<number | null>(null);
  const narrow = useNarrow();

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      if (startedAt.current) setElapsed((Date.now() - startedAt.current) / 1000);
    }, 200);
    return () => clearInterval(timer);
  }, [running]);

  function handle(message: Message) {
    switch (message.type) {
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
        setNote(`נמצא ב־${message.total_guesses} ניחושים`);
        setRunning(false);
        break;
      case "failed":
        setNote(message.reason);
        setRunning(false);
        break;
    }
  }

  async function solve() {
    setGuesses([]);
    setAnswer(null);
    setHypothesis(null);
    setNote(null);
    setElapsed(0);
    setLogOpen(false);
    startedAt.current = Date.now();
    setRunning(true);
    try {
      await startSolve(handle);
    } catch {
      setNote("השרת לא זמין. הפעילו אותו עם python -m uvicorn server.app:app");
      setRunning(false);
    }
  }

  const best = guesses.reduce<Guess | null>(
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
      <Board guesses={guesses} answer={answer} hypothesis={hypothesis} />

      {guesses.length === 0 && !running && <Opening />}

      <Log
        guesses={guesses}
        narrow={narrow}
        open={logOpen}
        onClose={() => setLogOpen(false)}
      />

      <Rail
        running={running}
        solved={answer !== null}
        best={best?.word ?? null}
        bestScore={best?.similarity ?? 0}
        count={guesses.length}
        elapsed={elapsed}
        note={note}
        narrow={narrow}
        hasLog={guesses.length > 0}
        onOpenLog={() => setLogOpen(true)}
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
        מרחב המשמעות
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
