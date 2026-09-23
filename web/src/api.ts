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

/** Set VITE_API_URL at build time to point at the deployed server. */
const SERVER = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SESSION_KEY = "semantle.session";

/**
 * The published site reads a run that was solved earlier by a scheduled
 * job, so there is no server to wait for. Set VITE_LIVE_SOLVER=true during
 * development to watch a real search against the game instead.
 */
export const LIVE_SOLVER = import.meta.env.VITE_LIVE_SOLVER === "true";
const RECORDING_URL = `${import.meta.env.BASE_URL}daily.json`;

/**
 * A run that never reached 100% is not published to the site, but its
 * events are dropped here locally (see scripts/publish_daily.py) so a
 * stuck search can still be replayed on the board for diagnosis, via
 * ?debug=failed.
 */
const FAILED_RUN_URL = `${import.meta.env.BASE_URL}daily-failed.json`;

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

/**
 * Join the day's run. Any previous connection must be closed by the caller.
 *
 * `recorded` says the search already finished and what arrives is the
 * recording, so the page knows to play it back rather than drop twenty
 * points on the board at once.
 */
export async function startSolve(
  handlers: Handlers,
): Promise<{ connection: Connection; recorded: boolean }> {
  const response = await fetch(`${SERVER}/api/solve/start`, { method: "POST" });
  if (!response.ok) throw new Error(`השרת החזיר ${response.status}`);
  const { session_id, recorded } = await response.json();
  rememberSession(session_id);
  return { connection: open(session_id, handlers), recorded: Boolean(recorded) };
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

export type Recording = {
  answer: string | null;
  recorded_at: string;
  events: Message[];
};

async function fetchRecording(url: string): Promise<Recording | null> {
  try {
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) return null;
    const recording = await response.json();
    return Array.isArray(recording?.events) ? recording : null;
  } catch {
    return null;
  }
}

/** The run published by the scheduled job, or null if none is there yet. */
export function loadRecording(): Promise<Recording | null> {
  return fetchRecording(RECORDING_URL);
}

/**
 * The most recent run that never reached the answer, or null if there is
 * none on hand. Its `answer` is always null. See FAILED_RUN_URL.
 */
export function loadFailedRun(): Promise<Recording | null> {
  return fetchRecording(FAILED_RUN_URL);
}
