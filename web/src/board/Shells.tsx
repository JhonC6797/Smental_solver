/**
 * The reference shells: the board's distance scale.
 *
 * Each shell is drawn as the silhouette of a sphere — a circle that always
 * faces the camera. That is exactly what a sphere of that radius looks like
 * from any angle, so the scale stays honest however the board is turned,
 * and it reads as a clean range ring rather than the moiré a wireframe
 * sphere makes.
 *
 * The labels all sit on one diagonal ray, so they separate by radius
 * instead of colliding. Shells get denser as the camera closes in, the way
 * a map's scale bar changes with zoom: far out, 25/50/75; close in, also
 * 85/90/95, which is where the search actually finishes.
 */

import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Billboard, Html, Line } from "@react-three/drei";
import * as THREE from "three";

import { CLOSE_RANGE, COLOR, SHELLS, radiusFor } from "./theme";

/** Where on each ring the label sits, in radians. Up and to the left. */
const LABEL_ANGLE = (Math.PI * 3) / 4;
const SEGMENTS = 96;

function circle(radius: number): [number, number, number][] {
  return Array.from({ length: SEGMENTS + 1 }, (_, i) => {
    const angle = (i / SEGMENTS) * Math.PI * 2;
    return [Math.cos(angle) * radius, Math.sin(angle) * radius, 0];
  });
}

function Shell({
  score,
  label,
  always,
}: {
  score: number;
  label: string;
  always: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const labelBox = useRef<HTMLDivElement>(null);
  const roomy = useThree((state) => state.size.width) >= 760;
  const radius = radiusFor(score);
  const points = useMemo(() => circle(radius), [radius]);

  useFrame(({ camera }) => {
    const shown = always || camera.position.length() < CLOSE_RANGE;
    if (group.current) group.current.visible = shown;
    // drei's Html renders into the DOM and does not inherit the group's
    // visibility, so the label has to be hidden by hand.
    if (labelBox.current) labelBox.current.style.display = shown ? "block" : "none";
  });

  return (
    <Billboard>
      <group ref={group}>
        <Line
          points={points}
          color={COLOR.rule}
          transparent
          opacity={score === 0 ? 0.45 : always ? 0.85 : 0.6}
          lineWidth={1}
        />
        {score > 0 && (
        <Html
          position={[
            Math.cos(LABEL_ANGLE) * radius,
            Math.sin(LABEL_ANGLE) * radius,
            0,
          ]}
          center
          zIndexRange={[4, 0]}
        >
          <div
            ref={labelBox}
            style={{
              whiteSpace: "nowrap",
              color: COLOR.inkFaint,
              fontFamily: "Assistant, system-ui, sans-serif",
              fontSize: 12,
              fontWeight: 600,
              background: COLOR.field,
              padding: "1px 7px",
              pointerEvents: "none",
              userSelect: "none",
            }}
          >
            <span className="figure">{score}%</span>
            {label && roomy && (
              <span style={{ fontWeight: 400, marginInlineStart: 7 }}>{label}</span>
            )}
          </div>
        </Html>
        )}
      </group>
    </Billboard>
  );
}

export function Shells() {
  return (
    <>
      {SHELLS.map((shell) => (
        <Shell key={shell.score} {...shell} />
      ))}
    </>
  );
}
