/**
 * The hidden word.
 *
 * It sits at the centre because that is what every guess is measured
 * against. While the search runs it is an empty setting — a slowly turning
 * cage with a question mark above it. When the answer arrives the cage
 * stops and the word takes its place in gold. That reveal is the one piece
 * of motion on the board that nobody asked for; everything else moves only
 * in answer to the solver or the pointer.
 */

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

import { COLOR } from "./theme";

const REDUCED_MOTION =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function Centre({ answer }: { answer: string | null }) {
  const cage = useRef<THREE.Mesh>(null);

  useFrame((_state, delta) => {
    if (!cage.current || answer || REDUCED_MOTION) return;
    cage.current.rotation.y += delta * 0.3;
    cage.current.rotation.x += delta * 0.12;
  });

  return (
    <group>
      {/* Small enough to sit inside the 95% shell rather than swallow it. */}
      <mesh ref={cage} visible={!answer}>
        <icosahedronGeometry args={[0.34, 0]} />
        <meshBasicMaterial color={COLOR.inkSoft} wireframe transparent opacity={0.7} />
      </mesh>

      {answer && (
        <mesh>
          <sphereGeometry args={[0.16, 20, 20]} />
          <meshBasicMaterial color={COLOR.record} />
        </mesh>
      )}

      {/* No distanceFactor: the marker stays legible at every zoom level. */}
      <Html center zIndexRange={[40, 0]}>
        <div
          style={{
            fontFamily: "'Frank Ruhl Libre', Georgia, serif",
            fontWeight: answer ? 700 : 400,
            fontSize: answer ? 40 : 26,
            lineHeight: 1,
            color: answer ? COLOR.record : COLOR.inkSoft,
            whiteSpace: "nowrap",
            pointerEvents: "none",
            userSelect: "none",
            transform: answer ? "translateY(-2.1em)" : "none",
            textShadow: `0 0 26px ${COLOR.field}, 0 0 10px ${COLOR.field}`,
            animation: answer && !REDUCED_MOTION ? "reveal 900ms ease-out" : "none",
          }}
        >
          {answer ?? "?"}
        </div>
      </Html>
    </group>
  );
}
