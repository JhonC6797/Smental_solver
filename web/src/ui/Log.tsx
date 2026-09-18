/**
 * The observation log.
 *
 * Every guess in the order it was made. It earns its place twice over: it
 * is how the board stays readable for anyone who cannot separate the two
 * mark colours, and it is the only place the exact numbers are written
 * down, which keeps them off the board itself.
 *
 * On a wide screen it is a fixed column beside the board. On a narrow one it
 * would cover half the board, so it becomes a panel that opens over it.
 */

import { useEffect, useRef } from "react";

import type { Guess } from "../api";
import { COLOR } from "../board/theme";

export function Log({
  guesses,
  narrow,
  open,
  onClose,
}: {
  guesses: Guess[];
  narrow: boolean;
  open: boolean;
  onClose: () => void;
}) {
  const scroller = useRef<HTMLOListElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [guesses.length]);

  if (guesses.length === 0) return null;
  if (narrow && !open) return null;

  return (
    <aside
      dir="rtl"
      style={{
        position: "absolute",
        insetInlineEnd: 0,
        top: 0,
        bottom: 68,
        zIndex: 20,
        width: narrow ? "100%" : 208,
        display: "flex",
        flexDirection: "column",
        borderInlineStart: `1px solid ${COLOR.rule}`,
        background: narrow ? COLOR.field : `${COLOR.field}d0`,
        backdropFilter: "blur(3px)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          padding: "14px 16px 8px",
        }}
      >
        <h2
          style={{
            margin: 0,
            fontFamily: "Assistant, system-ui, sans-serif",
            fontSize: 12,
            fontWeight: 600,
            color: COLOR.inkFaint,
          }}
        >
          יומן ניחושים
        </h2>
        {narrow && (
          <button
            onClick={onClose}
            style={{
              border: "none",
              background: "transparent",
              color: COLOR.inkSoft,
              fontSize: 14,
              cursor: "pointer",
              padding: 4,
            }}
          >
            סגור
          </button>
        )}
      </header>

      <ol
        ref={scroller}
        style={{
          margin: 0,
          padding: "0 8px 12px",
          listStyle: "none",
          overflowY: "auto",
          flex: 1,
        }}
      >
        {guesses.map((guess) => (
          <li
            key={guess.guess_number}
            style={{
              display: "grid",
              gridTemplateColumns: "22px 1fr auto",
              alignItems: "baseline",
              gap: 8,
              padding: "4px 8px",
              borderRadius: 2,
              background: guess.is_best_so_far ? `${COLOR.record}1a` : "transparent",
            }}
          >
            <span
              className="figure"
              style={{ fontSize: 11, color: COLOR.inkFaint, textAlign: "start" }}
            >
              {guess.guess_number}
            </span>
            <span
              style={{
                fontFamily: "'Frank Ruhl Libre', Georgia, serif",
                fontSize: 16,
                fontWeight: guess.is_best_so_far ? 700 : 400,
                color: guess.is_best_so_far ? COLOR.record : COLOR.ink,
              }}
            >
              {guess.word}
            </span>
            <span
              className="figure"
              style={{
                fontSize: 13,
                color: guess.is_best_so_far ? COLOR.record : COLOR.inkSoft,
              }}
            >
              {guess.similarity.toFixed(2)}
            </span>
          </li>
        ))}
      </ol>
    </aside>
  );
}
