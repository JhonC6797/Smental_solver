/**
 * The instrument rail.
 *
 * The board is the thing worth looking at, so the readouts live in the
 * margin the way annotations sit at the edge of a chart — a single rule and
 * a row of values, not a deck of cards competing with the visualization.
 */

import { COLOR } from "../board/theme";

export function Rail({
  running,
  solved,
  best,
  bestScore,
  count,
  elapsed,
  note,
  narrow,
  hasLog,
  onOpenLog,
  onSolve,
}: {
  running: boolean;
  solved: boolean;
  best: string | null;
  bestScore: number;
  count: number;
  elapsed: number;
  note: string | null;
  narrow: boolean;
  hasLog: boolean;
  onOpenLog: () => void;
  onSolve: () => void;
}) {
  return (
    <div
      dir="rtl"
      style={{
        position: "absolute",
        insetInline: 0,
        bottom: 0,
        zIndex: 10,
        display: "flex",
        alignItems: "center",
        gap: narrow ? 16 : 32,
        padding: narrow ? "0 14px" : "0 24px",
        height: 68,
        borderTop: `1px solid ${COLOR.rule}`,
        background: `linear-gradient(to top, ${COLOR.field} 55%, transparent)`,
      }}
    >
      <button
        onClick={onSolve}
        disabled={running}
        style={{
          fontFamily: "Assistant, system-ui, sans-serif",
          fontSize: 15,
          fontWeight: 600,
          padding: narrow ? "9px 14px" : "9px 20px",
          whiteSpace: "nowrap",
          borderRadius: 2,
          border: `1px solid ${running ? COLOR.rule : COLOR.record}`,
          background: "transparent",
          color: running ? COLOR.inkFaint : COLOR.record,
          cursor: running ? "default" : "pointer",
          transition: "background 160ms, color 160ms",
        }}
        onMouseEnter={(event) => {
          if (running) return;
          event.currentTarget.style.background = COLOR.record;
          event.currentTarget.style.color = COLOR.field;
        }}
        onMouseLeave={(event) => {
          event.currentTarget.style.background = "transparent";
          event.currentTarget.style.color = COLOR.record;
        }}
      >
        {running ? "מחפש" : solved ? "חפש שוב" : narrow ? "מצא את המילה" : "מצא את המילה של היום"}
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

      {narrow && hasLog && (
        <button
          onClick={onOpenLog}
          style={{
            marginInlineStart: "auto",
            border: `1px solid ${COLOR.rule}`,
            background: "transparent",
            color: COLOR.inkSoft,
            fontSize: 13,
            padding: "6px 12px",
            borderRadius: 2,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          יומן
        </button>
      )}

      {note && !narrow && (
        <span
          style={{
            marginInlineStart: "auto",
            fontSize: 14,
            color: solved ? COLOR.record : COLOR.inkSoft,
          }}
        >
          {note}
        </span>
      )}
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

/** How far the best guess has come, measured from the no-relation baseline. */
function Progress({ score }: { score: number }) {
  const start = 25;
  const share = Math.max(0, Math.min(1, (score - start) / (100 - start)));
  return (
    <div style={{ flex: "0 1 200px", minWidth: 90 }}>
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
