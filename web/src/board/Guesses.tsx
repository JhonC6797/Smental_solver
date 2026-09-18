/**
 * The guesses themselves.
 *
 * Distance from the centre is the score, exactly. Direction is meaning, so
 * words about the same thing land in the same quarter of the board. Colour
 * carries only one thing that position cannot: whether a guess was a new
 * best. "Worse than before" needs no colour — it is already visible as a
 * point further out.
 *
 * Two paths are drawn. The faint one follows every guess in order and shows
 * the search wandering; the gold one links only the records and shows the
 * progress that survived.
 */

import { useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

import type { Guess } from "../api";
import { COLOR } from "./theme";

/** Angular size of a dot: constant on screen, so zooming never inflates it. */
const DOT_SCALE = 0.009;
const RECORD_SCALE = 0.013;
const ARRIVAL_MS = 350;

/**
 * How much room a label needs to be worth drawing, and how many the board
 * will carry. A small screen holds the same board in less space, so it gets
 * smaller type and fewer names — the rest appear as the reader zooms in.
 */
const COMPACT_WIDTH = 760;
const SPACIOUS = { gapX: 58, gapY: 34, max: 14, word: 16, score: 12 };
const COMPACT = { gapX: 44, gapY: 26, max: 8, word: 13, score: 10 };
const DECLUTTER_INTERVAL_MS = 120;

const REDUCED_MOTION =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const vectorOf = (guess: Guess) =>
  new THREE.Vector3(guess.position.x, guess.position.y, guess.position.z);

export function Guesses({
  guesses,
  answer,
}: {
  guesses: Guess[];
  answer: string | null;
}) {
  const dots = useRef<(THREE.Mesh | null)[]>([]);
  const born = useRef<Map<number, number>>(new Map());
  const lastDeclutter = useRef(0);
  const [labelled, setLabelled] = useState<number[]>([]);
  const [hovered, setHovered] = useState<number | null>(null);
  const { camera, size } = useThree();
  const metrics = size.width < COMPACT_WIDTH ? COMPACT : SPACIOUS;

  const points = useMemo(() => guesses.map(vectorOf), [guesses]);

  const recordPath = useMemo(() => {
    const records = guesses.filter((guess) => guess.is_best_so_far).map(vectorOf);
    return records.length >= 2 ? records : null;
  }, [guesses]);

  useFrame(({ clock }) => {
    const now = clock.getElapsedTime() * 1000;

    // Keep every dot the same size on screen, and let new ones arrive.
    guesses.forEach((guess, index) => {
      const dot = dots.current[index];
      if (!dot) return;
      if (!born.current.has(guess.guess_number)) {
        born.current.set(guess.guess_number, now);
      }
      const age = now - (born.current.get(guess.guess_number) ?? now);
      const arrival = REDUCED_MOTION ? 1 : Math.min(1, age / ARRIVAL_MS);
      const eased = 1 - Math.pow(1 - arrival, 3);
      const base = guess.is_best_so_far ? RECORD_SCALE : DOT_SCALE;
      const emphasis = hovered === guess.guess_number ? 1.7 : 1;
      const distance = camera.position.distanceTo(dot.position);
      dot.scale.setScalar(distance * base * eased * emphasis);
    });

    if (now - lastDeclutter.current < DECLUTTER_INTERVAL_MS) return;
    lastDeclutter.current = now;
    setLabelled(declutter(guesses, points, camera, size, hovered, metrics));
  });

  return (
    <>
      {points.length >= 2 && (
        <Line
          points={points}
          color={COLOR.inkFaint}
          transparent
          opacity={0.09}
          lineWidth={1}
        />
      )}
      {recordPath && (
        <Line
          points={recordPath}
          color={COLOR.record}
          transparent
          opacity={0.36}
          lineWidth={1.5}
        />
      )}

      {guesses.map((guess, index) => {
        const isAnswer = answer !== null && guess.word === answer;
        return (
          <mesh
            key={guess.guess_number}
            ref={(mesh) => {
              dots.current[index] = mesh;
            }}
            position={[guess.position.x, guess.position.y, guess.position.z]}
            onPointerOver={(event) => {
              event.stopPropagation();
              setHovered(guess.guess_number);
            }}
            onPointerOut={() => setHovered(null)}
            visible={!isAnswer}
          >
            <sphereGeometry args={[1, 14, 14]} />
            <meshBasicMaterial
              color={guess.is_best_so_far ? COLOR.record : COLOR.observation}
            />
          </mesh>
        );
      })}

      {guesses
        .filter(
          (guess) =>
            labelled.includes(guess.guess_number) &&
            !(answer !== null && guess.word === answer),
        )
        .map((guess) => (
          <Html
            key={guess.guess_number}
            position={[guess.position.x, guess.position.y, guess.position.z]}
            center
            zIndexRange={[20, 0]}
          >
            <Label
              guess={guess}
              active={hovered === guess.guess_number}
              metrics={metrics}
            />
          </Html>
        ))}
    </>
  );
}

type Metrics = typeof SPACIOUS;

function Label({
  guess,
  active,
  metrics,
}: {
  guess: Guess;
  active: boolean;
  metrics: Metrics;
}) {
  return (
    <div
      style={{
        transform: `translateY(${guess.is_best_so_far ? "-2.3em" : "-1.9em"})`,
        whiteSpace: "nowrap",
        pointerEvents: "none",
        userSelect: "none",
        textAlign: "center",
        lineHeight: 1.15,
      }}
    >
      <div
        style={{
          fontFamily: "'Frank Ruhl Libre', Georgia, serif",
          fontSize: active ? metrics.word + 3 : metrics.word,
          fontWeight: guess.is_best_so_far ? 700 : 400,
          color: guess.is_best_so_far ? COLOR.record : COLOR.ink,
          textShadow: `0 0 10px ${COLOR.field}, 0 0 4px ${COLOR.field}`,
        }}
      >
        {guess.word}
      </div>
      <div
        className="figure"
        style={{
          fontFamily: "Assistant, system-ui, sans-serif",
          fontSize: metrics.score,
          color: COLOR.inkSoft,
          textShadow: `0 0 8px ${COLOR.field}`,
        }}
      >
        {guess.similarity.toFixed(1)}
        {active && guess.rank !== null && ` · מקום ${guess.rank} מתוך 1000`}
      </div>
    </div>
  );
}

/**
 * Choose which labels to draw, the way a map thins its place names: take
 * them in order of importance and keep one only if it has room to be read.
 * Everything else waits until the camera comes closer and makes room.
 */
function declutter(
  guesses: Guess[],
  points: THREE.Vector3[],
  camera: THREE.Camera,
  size: { width: number; height: number },
  hovered: number | null,
  metrics: Metrics,
): number[] {
  const ranked = guesses
    .map((guess, index) => ({ guess, point: points[index] }))
    .sort((a, b) => {
      if (a.guess.guess_number === hovered) return -1;
      if (b.guess.guess_number === hovered) return 1;
      if (a.guess.is_best_so_far !== b.guess.is_best_so_far) {
        return a.guess.is_best_so_far ? -1 : 1;
      }
      return b.guess.similarity - a.guess.similarity;
    });

  const taken: { x: number; y: number }[] = [];
  const chosen: number[] = [];

  for (const { guess, point } of ranked) {
    if (chosen.length >= metrics.max) break;
    const projected = point.clone().project(camera);
    if (projected.z > 1) continue; // behind the camera
    const x = ((projected.x + 1) / 2) * size.width;
    const y = ((1 - projected.y) / 2) * size.height;
    const collides = taken.some(
      (other) =>
        Math.abs(other.x - x) < metrics.gapX && Math.abs(other.y - y) < metrics.gapY,
    );
    if (collides) continue;
    taken.push({ x, y });
    chosen.push(guess.guess_number);
  }

  return chosen;
}
