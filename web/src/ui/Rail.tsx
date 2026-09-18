/**
 * The instrument rail.
 *
 * The board is the thing worth looking at, so the readouts live in the
 * margin the way annotations sit at the edge of a chart — a single rule and
 * a row of values, not a deck of cards competing with the visualization.
 * The primary action sits at the start of the row; the views you can turn
 * on and off sit at the far end, out of the way until wanted.
 */

import { COLOR } from "../board/theme";

export function Rail({
  running,
  replaying,
  solved,
  best,
  bestScore,
  count,
  elapsed,
  note,
  narrow,
  logOpen,
  chartOpen,
  canReplay,
  onToggleLog,
  onToggleChart,
  onReplay,
  onSolve,
}: {
  running: boolean;
  replaying: boolean;
  solved: boolean;
  best: string | null;
  bestScore: number;
  count: number;
  elapsed: number;
  note: string | null;
  narrow: boolean;
  logOpen: boolean;
  chartOpen: boolean;
  canReplay: boolean;
  onToggleLog: () => void;
  onToggleChart: () => void;
  onReplay: () => void;
  onSolve: () => void;
}) {
  const busy = running || replaying;

  return (
    <div
      dir="rtl"
      style={{
        position: "absolute",
        insetInline: 0,
        bottom: 0,
        zIndex: 30,
        display: "flex",
        alignItems: "center",
        gap: narrow ? 12 : 26,
        padding: narrow ? "0 12px" : "0 20px",
        height: 68,
        borderTop: `1px solid ${COLOR.rule}`,
        background: `linear-gradient(to top, ${COLOR.field} 55%, ${COLOR.field}e0)`,
      }}
    >
      <button
        onClick={onSolve}
        disabled={busy}
        style={{
          fontFamily: "Assistant, system-ui, sans-serif",
          fontSize: 15,
          fontWeight: 600,
          padding: narrow ? "9px 14px" : "9px 20px",
          borderRadius: 2,
          whiteSpace: "nowrap",
          border: `1px solid ${busy ? COLOR.rule : COLOR.record}`,
          background: "transparent",
          color: busy ? COLOR.inkFaint : COLOR.record,
          cursor: busy ? "default" : "pointer",
          transition: "background 160ms, color 160ms",
        }}
        onMouseEnter={(event) => {
          if (busy) return;
          event.currentTarget.style.background = COLOR.record;
          event.currentTarget.style.color = COLOR.field;
        }}
        onMouseLeave={(event) => {
          event.currentTarget.style.background = "transparent";
          event.currentTarget.style.color = busy ? COLOR.inkFaint : COLOR.record;
        }}
      >
        {running
          ? "מחפש"
          : replaying
            ? "מריץ שוב"
            : solved
              ? "חפש שוב"
              : narrow
                ? "מצא את המילה"
                : "מצא את המילה של היום"}
      </button>

      {best && (
        <Readout label="הקרוב ביותר">
          <span
            style={{
              fontFamily: "'Frank Ruhl Libre', Georgia, serif",
              fontSize: 22,
              fontWeight: 700,
              color: COLOR.record,
            }}
          >
            {best}
          </span>
          <span
            className="figure"
            style={{ marginInlineStart: 10, fontSize: 15, color: COLOR.inkSoft }}
          >
            {bestScore.toFixed(2)}
          </span>
        </Readout>
      )}

      <Readout label="ניחושים">
        <span className="figure" style={{ fontSize: 20 }}>
          {count}
        </span>
      </Readout>

      {!narrow && (
        <Readout label="זמן">
          <span className="figure" style={{ fontSize: 20 }}>
            {formatElapsed(elapsed)}
          </span>
        </Readout>
      )}

      {!narrow && best && !solved && <Progress score={bestScore} />}

      {note && !narrow && (
        <span style={{ fontSize: 14, color: solved ? COLOR.record : COLOR.inkSoft }}>
          {note}
        </span>
      )}

      <div
        style={{
          marginInlineStart: "auto",
          display: "flex",
          gap: 8,
          alignItems: "center",
        }}
      >
        {canReplay && (
          <Toggle active={false} disabled={busy} onClick={onReplay}>
            הרצה חוזרת
          </Toggle>
        )}
        {count > 0 && (
          <Toggle active={chartOpen} onClick={onToggleChart}>
            גרף
          </Toggle>
        )}
        {count > 0 && (
          <Toggle active={logOpen} onClick={onToggleLog}>
            יומן
          </Toggle>
        )}
      </div>
    </div>
  );
}

function Readout({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
      <span style={{ fontSize: 11, color: COLOR.inkFaint, fontWeight: 400 }}>
        {label}
      </span>
      <span style={{ color: COLOR.ink }}>{children}</span>
    </div>
  );
}

function Toggle({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      style={{
        border: `1px solid ${active ? COLOR.inkSoft : COLOR.rule}`,
        background: active ? `${COLOR.inkSoft}1a` : "transparent",
        color: disabled ? COLOR.inkFaint : active ? COLOR.ink : COLOR.inkSoft,
        fontSize: 13,
        padding: "6px 12px",
        borderRadius: 2,
        cursor: disabled ? "default" : "pointer",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

/** How far the best guess has come, measured from the no-relation baseline. */
function Progress({ score }: { score: number }) {
  const start = 25;
  const share = Math.max(0, Math.min(1, (score - start) / (100 - start)));
  return (
    <div style={{ flex: "0 1 180px", minWidth: 80 }}>
      <div style={{ height: 3, background: COLOR.rule, borderRadius: 2 }}>
        <div
          style={{
            height: "100%",
            width: `${share * 100}%`,
            background: COLOR.record,
            borderRadius: 2,
            transition: "width 400ms ease-out",
          }}
        />
      </div>
    </div>
  );
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}
