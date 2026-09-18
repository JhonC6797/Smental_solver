/**
 * Frames the whole board, whatever shape the window is.
 *
 * A perspective camera's field of view is vertical, so on a tall narrow
 * phone the horizontal extent runs out first and half the guesses fall
 * outside the frame. This works out the distance at which the board fits in
 * both directions, raises the zoom-out limit to match, and only then moves
 * the camera — the other order lets the controls clamp the move back to the
 * old limit.
 */

import { useEffect } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

import { BOARD_RADIUS } from "./theme";

/** A little air around the outermost shell. */
const MARGIN = 1.08;

export function FitToViewport() {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);
  const controls = useThree((state) => state.controls) as
    | { maxDistance: number; update: () => void }
    | null;

  useEffect(() => {
    const perspective = camera as THREE.PerspectiveCamera;
    const halfHeight = Math.tan((perspective.fov * Math.PI) / 360);
    const aspect = size.width / size.height;
    const distance =
      (BOARD_RADIUS * MARGIN) / Math.min(halfHeight, halfHeight * aspect);

    if (controls) {
      controls.maxDistance = distance;
      camera.position.setLength(distance);
      controls.update();
    } else {
      camera.position.setLength(distance);
    }
    camera.updateProjectionMatrix();
  }, [camera, controls, size.width, size.height]);

  return null;
}
