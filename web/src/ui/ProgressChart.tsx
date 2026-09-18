/**
 * Score per guess, with the running best above it.
 *
 * The board shows where the search went. This shows how fast it got there —
 * the plateaus where nothing improved, and the jumps where it did. Same two
 * colours as the board, so a gold mark means the same thing in both views.
 *
 * Drawn as plain SVG: two series over twenty points needs no chart library,
 * and hand-drawing it keeps the marks thin and the grid recessive.
 */

import { useLayoutEffect, useRef, useState } from "react";

import type { Guess } from "../api";
import { COLOR } from "../board/theme";

const HEIGHT = 190;
/** Room on the left for the series names, on the right for the y scale. */
const PAD = { top: 20, right: 40, bottom: 26, left: 74 };
/** Unrelated words score about this, so it is the floor worth marking. */
const BASELINE = 25;

export function ProgressChart({
  guesses,
  highlighted,
  onHighlight,
}: {
  guesses: Guess[];
  highlighted: number | null;
  onHighlight: (guessNumber: number | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);

  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(entry.contentRect.width),
    );
    observer.observe(element);
    setWidth(element.clientWidth);
    return () => observer.disconnect();
  }, []);

  const plotWidth = Math.max(120, width - PAD.left - PAD.right);
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const last = Math.max(guesses.length, 2);

  // Guess 1 sits on the right and the run advances leftwards, the way the
  // rest of the interface reads.
  const x = (n: number) =>
    PAD.left + plotWidth - ((n - 1) / (last - 1)) * plotWidth;
  const y = (score: number) => PAD.top + (1 - score / 100) * plotHeight;

  const scorePath = guesses
    .map((g, i) => `${i === 0 ? "M" : "L"}${x(g.guess_number)} ${y(g.similarity)}`)
    .join(" ");

  // The best is a record of what was known at each step, so it holds its
  // value until it changes: a step line, not a slope.
  const bestPath = guesses
    .flatMap((g, i) =>
      i === 0
        ? [`M${x(g.guess_number)} ${y(g.best_similarity)}`]
        : [
            `L${x(g.guess_number)} ${y(guesses[i - 1].best_similarity)}`,
            `L${x(g.guess_number)} ${y(g.best_similarity)}`,
          ],
    )
    .join(" ");

  const active = guesses.find((g) => g.guess_number === highlighted) ?? null;

  function pick(event: React.MouseEvent<SVGSVGElement>) {
    if (guesses.length === 0) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const offset = event.clientX - bounds.left;
    const nearest = guesses.reduce((best, g) =>
      Math.abs(x(g.guess_number) - offset) < Math.abs(x(best.guess_number) - offset)
        ? g
        : best,
    );
    onHighlight(nearest.guess_number);
  }

  return (
    <div ref={box} style={{ width: "100%" }}>
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label="ציון כל ניחוש לאורך הריצה, עם השיא המצטבר"
        onMouseMove={pick}
        onMouseLeave={() => onHighlight(null)}
        /* SVG resolves text-anchor against the writing direction, so inside
           an RTL panel "start" would mean the right edge and every label
           would stretch the wrong way. The geometry here is stated in plain
           left-to-right terms. */
        direction="ltr"
        style={{ display: "block", cursor: "crosshair" }}
      >
        {[0, 25, 50, 75, 100].map((score) => (
          <g key={score}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotWidth}
              y1={y(score)}
              y2={y(score)}
              stroke={COLOR.rule}
              strokeWidth={1}
              strokeDasharray={score === BASELINE ? "3 4" : undefined}
              opacity={score === BASELINE ? 0.9 : 0.45}
            />
            <text
              x={PAD.left + plotWidth + 8}
              y={y(score) + 4}
              textAnchor="start"
              fill={COLOR.inkFaint}
              fontSize={11}
              fontFamily="Assistant, system-ui, sans-serif"
            >
              {score}
            </text>
          </g>
        ))}

        <text
          x={PAD.left + plotWidth - 6}
          y={y(BASELINE) - 6}
          textAnchor="end"
          fill={COLOR.inkFaint}
          fontSize={11}
          fontFamily="Assistant, system-ui, sans-serif"
        >
          רף מילה אקראית
        </text>

        {guesses.length > 0 && (
          <>
            <path d={scorePath} fill="none" stroke={COLOR.observation} strokeWidth={1.5} />
            <path d={bestPath} fill="none" stroke={COLOR.record} strokeWidth={2} />

            {guesses.map((g) => (
              <circle
                key={g.guess_number}
                cx={x(g.guess_number)}
                cy={y(g.similarity)}
                r={g.guess_number === highlighted ? 5 : 3}
                fill={g.is_best_so_far ? COLOR.record : COLOR.observation}
                stroke={COLOR.field}
                strokeWidth={1.5}
              />
            ))}

            {/* Named in text, so the two series are never told apart by colour alone. */}
            {(() => {
              const latest = guesses[guesses.length - 1];
              const guessY = y(latest.similarity);
              const bestY = y(latest.best_similarity);
              // Both series finish at 100 on a solved run, so their names
              // have to be parted, and kept off the top edge.
              const floor = PAD.top + 8;
              const apart = Math.abs(guessY - bestY) >= 18;
              return (
                <>
                  <SeriesLabel
                    x={PAD.left + 10}
                    y={Math.max(floor + 18, apart ? guessY : bestY + 18)}
                    color={COLOR.observation}
                    text="ניחוש"
                  />
                  <SeriesLabel
                    x={PAD.left + 10}
                    y={Math.max(floor, bestY)}
                    color={COLOR.record}
                    text="שיא"
                  />
                </>
              );
            })()}
          </>
        )}

        {active && (
          <>
            <line
              x1={x(active.guess_number)}
              x2={x(active.guess_number)}
              y1={PAD.top}
              y2={PAD.top + plotHeight}
              stroke={COLOR.inkFaint}
              strokeWidth={1}
              opacity={0.6}
            />
            <text
              x={x(active.guess_number)}
              y={PAD.top - 5}
              textAnchor="middle"
              fill={COLOR.ink}
              fontSize={13}
              fontFamily="'Frank Ruhl Libre', Georgia, serif"
            >
              {active.word} {active.similarity.toFixed(1)}
            </text>
          </>
        )}

        <text
          x={PAD.left + plotWidth / 2}
          y={HEIGHT - 6}
          textAnchor="middle"
          fill={COLOR.inkFaint}
          fontSize={11}
          fontFamily="Assistant, system-ui, sans-serif"
        >
          מספר ניחוש
        </text>
      </svg>
    </div>
  );
}

function SeriesLabel({
  x,
  y,
  color,
  text,
}: {
  x: number;
  y: number;
  color: string;
  text: string;
}) {
  return (
    <>
      <circle cx={x - 6} cy={y - 4} r={3.5} fill={color} />
      <text
        x={x}
        y={y}
        textAnchor="start"
        fill={COLOR.inkSoft}
        fontSize={12}
        fontFamily="Assistant, system-ui, sans-serif"
      >
        {text}
      </text>
    </>
  );
}
