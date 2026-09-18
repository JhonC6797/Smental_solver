/**
 * The board's palette and geometry constants.
 *
 * The three mark colours were validated against the dark field for the
 * lightness band, chroma floor, colour-blind separation, normal-vision
 * separation and contrast. Do not substitute them by eye — re-run the
 * validator if they need to change.
 */

export const COLOR = {
  field: "#0f1a2b",
  rule: "#23344c",
  ink: "#e8dfcb",
  inkSoft: "#a9b3c4",
  inkFaint: "#6b788c",
  observation: "#3a8fc4",
  record: "#bc8022",
  hypothesis: "#8a68c4",
} as const;

/** Matches BOARD_RADIUS in server/projection.py: a score of 0 sits here. */
export const BOARD_RADIUS = 10;

/**
 * Reference shells, labelled by score.
 *
 * 25 is not a round number chosen for looks: unrelated Hebrew words score
 * 24-32 against the live game, so that shell is the honest "no relation"
 * baseline and everything inside it means something.
 */
export const SHELLS = [
  { score: 0, label: "", always: true },
  { score: 25, label: "רף מילה אקראית", always: true },
  { score: 50, label: "", always: true },
  { score: 75, label: "", always: true },
  { score: 85, label: "", always: false },
  { score: 90, label: "", always: false },
  { score: 95, label: "", always: false },
] as const;

export const radiusFor = (score: number) => BOARD_RADIUS * (1 - score / 100);

/** Zoom bounds: close enough to separate the endgame, never through the centre. */
export const MIN_DISTANCE = 1.6;
export const MAX_DISTANCE = 30;

/** Framed so the 25% shell — the no-relation baseline — sits inside the view. */
export const START_DISTANCE = 23;

/** Below this camera distance the dense shells (85/90/95) are drawn. */
export const CLOSE_RANGE = 11;
