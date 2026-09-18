/**
 * Where the algorithm believes the answer is.
 *
 * Drawn as a bearing from the centre rather than a point, because that is
 * what the estimate actually is: a direction in meaning, with no claim
 * about distance. Watching it swing as evidence arrives, and settle once
 * the search locks on, is the clearest view of the algorithm changing its
 * mind.
 */

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

import { BOARD_RADIUS, COLOR } from "./theme";

const EASING_PER_SECOND = 4;

/** The bearing is a direction, not a distance, so it stops short of the edge. */
const BEARING_LENGTH = 0.72;

export function Hypothesis({
  direction,
}: {
  direction: [number, number, number] | null;
}) {
  const shown = useRef(new THREE.Vector3(0, 0, 0));
  const line = useRef<any>(null);
  const tip = useRef<THREE.Mesh>(null);
  const target = useRef(new THREE.Vector3(0, 0, 0));

  if (direction) {
    target.current.set(...direction).normalize().multiplyScalar(BOARD_RADIUS * BEARING_LENGTH);
  }

  useFrame((_state, delta) => {
    if (!direction) return;
    // Ease towards the new bearing so a swing reads as a decision, not a jump.
    shown.current.lerp(target.current, Math.min(1, delta * EASING_PER_SECOND));
    tip.current?.position.copy(shown.current);
    line.current?.geometry?.setPositions?.([
      0,
      0,
      0,
      shown.current.x,
      shown.current.y,
      shown.current.z,
    ]);
  });

  if (!direction) return null;

  return (
    <group>
      <Line
        ref={line}
        points={[
          [0, 0, 0],
          [target.current.x, target.current.y, target.current.z],
        ]}
        color={COLOR.hypothesis}
        transparent
        opacity={0.4}
        lineWidth={1.5}
        dashed
        dashSize={0.28}
        gapSize={0.22}
      />
      <mesh ref={tip}>
        <tetrahedronGeometry args={[0.16, 0]} />
        <meshBasicMaterial color={COLOR.hypothesis} />
      </mesh>
    </group>
  );
}
