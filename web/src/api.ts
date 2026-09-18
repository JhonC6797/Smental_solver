/**
 * The wire protocol, and the connection that carries it.
 *
 * These types mirror server/serialization.py. The core message kinds
 * (run_started, guess, solved, failed) are stable across any search
 * algorithm; `diagnostics` is deliberately open, and must be rendered by
 * value type rather than by key name, so replacing the algorithm never
 * requires a change here.
 *
 * A run's id is kept in sessionStorage so a reload can rejoin it. The
 * server replays everything that already happened before following the
 * live stream, so nothing is lost.
 */

const SERVER = "http://localhost:8000";
const SESSION_KEY = "semantle.session";

export type Position = { x: number; y: number; z: number; radius: number };

export type Message =
  | { type: "run_started"; vocabulary_size: number; started_at: string }
  | {
      type: "guess";
      word: string;
      similarity: number;
      rank: number | null;
      guess_number: number;
      is_best_so_far: boolean;
      best_word: string;
      best_similarity: number;
      position: Position;
    }
  | { type: "solved"; word: string; total_guesses: number; elapsed_seconds: number }
  | { type: "failed"; reason: string }
  | {
      type: "diagnostics";
      guess_number: number;
      scalars: Record<string, number>;
      directions: Record<string, [number, number, number]>;
      word_scores: Record<string, [string, number][]>;
    };

export type Guess = Extract<Message, { type: "guess" }>;

export type Handlers = {
  onMessage: (message: Message) => void;
  /** Called once when the run can no longer be followed, with a reason. */
  onLost: (reason: string) => void;
};

export type Connection = { close: () => void };

/** A closed connection, so callers never have to null-check. */
const CLOSED: Connection = { close: () => {} };

function open(sessionId: string, handlers: Handlers): Connection {
  const socket = new WebSocket(
    `${SERVER.replace("http", "ws")}/ws/solve/${sessionId}`,
  );
  let finished = false;
  let deliberate = false;

  socket.onmessage = (event) => {
    const message: Message = JSON.parse(event.data);
    if (message.type === "solved" || message.type === "failed") {
      finished = true;
      forgetSession();
    }
    handlers.onMessage(message);
  };

  socket.onerror = () => {
    if (!finished && !deliberate) handlers.onLost("החיבור לשרת נכשל");
  };

  socket.onclose = (event) => {
    if (finished || deliberate) return;
    forgetSession();
    handlers.onLost(
      event.code === 4004
        ? "הריצה כבר לא קיימת בשרת"
        : "החיבור לשרת נותק באמצע הריצה",
    );
  };

  return {
    close: () => {
      deliberate = true;
      socket.close();
    },
  };
}

/** Start a new run. Any previous connection must be closed by the caller. */
export async function startSolve(handlers: Handlers): Promise<Connection> {
  const response = await fetch(`${SERVER}/api/solve/start`, { method: "POST" });
  if (!response.ok) throw new Error(`השרת החזיר ${response.status}`);
  const { session_id } = await response.json();
  rememberSession(session_id);
  return open(session_id, handlers);
}

/** Rejoin the run this browser was watching, if there was one. */
export function rejoinSolve(handlers: Handlers): Connection | null {
  const sessionId = readSession();
  return sessionId === null ? null : open(sessionId, handlers);
}

export function hasSession(): boolean {
  return readSession() !== null;
}

function readSession(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null; // private browsing, or storage blocked
  }
}

function rememberSession(sessionId: string): void {
  try {
    sessionStorage.setItem(SESSION_KEY, sessionId);
  } catch {
    /* the run still works, it just cannot be rejoined after a reload */
  }
}

function forgetSession(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* nothing to clean up */
  }
}

export { CLOSED };
