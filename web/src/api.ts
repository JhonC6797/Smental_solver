/**
 * The wire protocol.
 *
 * These types mirror server/serialization.py. The core message kinds
 * (run_started, guess, solved, failed) are stable across any search
 * algorithm; `diagnostics` is deliberately open, and must be rendered by
 * value type rather than by key name, so replacing the algorithm never
 * requires a change here.
 */

const SERVER = "http://localhost:8000";

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

export async function startSolve(
  onMessage: (message: Message) => void,
): Promise<WebSocket> {
  const response = await fetch(`${SERVER}/api/solve/start`, { method: "POST" });
  const { session_id } = await response.json();
  const socket = new WebSocket(
    `${SERVER.replace("http", "ws")}/ws/solve/${session_id}`,
  );
  socket.onmessage = (event) => onMessage(JSON.parse(event.data));
  return socket;
}
