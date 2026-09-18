/**
 * True on screens too narrow to show the board and the log side by side.
 *
 * Below this width the log would cover half the board, so it becomes a panel
 * the reader opens instead of a fixed column.
 */

import { useEffect, useState } from "react";

const NARROW = "(max-width: 760px)";

export function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(
    () => typeof window !== "undefined" && window.matchMedia(NARROW).matches,
  );

  useEffect(() => {
    const query = window.matchMedia(NARROW);
    const update = (event: MediaQueryListEvent) => setNarrow(event.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return narrow;
}
