/**
 * The observation log.
 *
 * Every guess in the order it was made. It earns its place twice over: it
 * is how the board stays readable for anyone who cannot separate the two
 * mark colours, and it is the only place the exact numbers are written
 * down, which keeps them off the board itself.
 *
 * Pointing at a row lights the matching point on the board, and the filter
 * here governs the board too — "records only" is a way of reading the
 * search, not a way of reading this list.
 *
 * On a wide screen it is a column beside the board; on a narrow one it
 * would cover half of it, so it opens over the board instead.
 */

import { useEffect, useRef } from "react";

import type { Guess } from "../api";
import { COLOR } from "../board/theme";

export function Log({
  guesses,
  narrow,
  recordsOnly,
  highlighted,
  onFilter,
  onHighlight,
  onClose,
}: {
  guesses: Guess[];
  narrow: boolean;
  recordsOnly: boolean;
  highlighted: number | null;
  onFilter: (recordsOnly: boolean) => void;
  onHighlight: (guessNumber: number | null) => void;
  onClose: () => void;
}) {
  const scroller = useRef<HTMLOListElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [guesses.length]);

  const rows = recordsOnly ? guesses.filter((g) => g.is_best_so_far) : guesses;

  return (
    <aside
      dir="rtl"
      style={{
        position: "absolute",
        insetInlineEnd: 0,
        top: 0,
        bottom: 68,
        zIndex: 28,
        width: narrow ? "100%" : 224,
        display: "flex",
        flexDirection: "column",
        borderInlineStart: `1px solid ${COLOR.rule}`,
        background: narrow ? COLOR.field : `${COLOR.field}d8`,
        backdropFilter: "blur(3px)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 12px 8px 8px",
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
        <button
          onClick={onClose}
          aria-label="סגור את היומן"
          style={{
            border: "none",
            background: "transparent",
            color: COLOR.inkSoft,
            fontSize: 13,
            cursor: "pointer",
            padding: 4,
          }}
        >
          סגור
        </button>
      </header>

      <div style={{ display: "flex", gap: 6, padding: "0 12px 10px" }}>
        <Choice active={!recordsOnly} onClick={() => onFilter(false)}>
          הכל {guesses.length}
        </Choice>
        <Choice active={recordsOnly} onClick={() => onFilter(true)}>
          שיאים {guesses.filter((g) => g.is_best_so_far).length}
        </Choice>
      </div>

      {rows.length === 0 ? (
        <p
          style={{
            margin: 0,
            padding: "8px 16px",
            fontSize: 13,
            color: COLOR.inkFaint,
          }}
        >
          {guesses.length === 0
            ? "הריצה עוד לא התחילה."
            : "עוד לא נרשם שיא בריצה הזו."}
        </p>
      ) : (
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
          {rows.map((guess) => (
            <li
              key={guess.guess_number}
              onMouseEnter={() => onHighlight(guess.guess_number)}
              onMouseLeave={() => onHighlight(null)}
              style={{
                display: "grid",
                gridTemplateColumns: "22px 1fr auto",
                alignItems: "baseline",
                gap: 8,
                padding: "4px 8px",
                borderRadius: 2,
                cursor: "default",
                outline:
                  guess.guess_number === highlighted
                    ? `1px solid ${COLOR.inkFaint}`
                    : "none",
                background: guess.is_best_so_far
                  ? `${COLOR.record}1a`
                  : guess.guess_number === highlighted
                    ? `${COLOR.observation}1a`
                    : "transparent",
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
      )}
    </aside>
  );
}

function Choice({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      style={{
        flex: 1,
        padding: "5px 8px",
        fontSize: 12,
        fontWeight: active ? 600 : 400,
        borderRadius: 2,
        border: `1px solid ${active ? COLOR.record : COLOR.rule}`,
        background: active ? `${COLOR.record}1f` : "transparent",
        color: active ? COLOR.record : COLOR.inkSoft,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}
