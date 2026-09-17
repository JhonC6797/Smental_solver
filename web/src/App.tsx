import { useState } from "react";
import { Board } from "./Board";
import { startSolve, type Guess, type Message } from "./api";

export default function App() {
  const [guesses, setGuesses] = useState<Guess[]>([]);
  const [status, setStatus] = useState("");
  const [running, setRunning] = useState(false);

  function handle(message: Message) {
    if (message.type === "guess") {
      setGuesses((previous) => [...previous, message]);
    } else if (message.type === "solved") {
      setStatus(`נפתר: ${message.word} · ${message.total_guesses} ניחושים`);
      setRunning(false);
    } else if (message.type === "failed") {
      setStatus(message.reason);
      setRunning(false);
    }
  }

  async function run() {
    setGuesses([]);
    setStatus("");
    setRunning(true);
    try {
      await startSolve(handle);
    } catch (error) {
      setStatus(String(error));
      setRunning(false);
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "#0b1020" }}>
      <div
        style={{
          position: "absolute",
          zIndex: 1,
          padding: 16,
          color: "#e8ecf8",
          fontFamily: "system-ui, sans-serif",
          direction: "rtl",
        }}
      >
        <button onClick={run} disabled={running} style={{ padding: "8px 16px" }}>
          {running ? "פותר..." : "פתור סמנטל של היום"}
        </button>
        <span style={{ marginRight: 12 }}>
          {guesses.length} ניחושים {status}
        </span>
      </div>
      <Board guesses={guesses} />
    </div>
  );
}
