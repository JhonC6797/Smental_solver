/**
 * The board: a ranging instrument for meaning.
 *
 * The hidden word is at the centre. Every guess is placed at a distance
 * set by its score and a direction set by its meaning, so the search reads
 * as a hunt closing in rather than a list of results. The default view
 * looks straight down, where the shells read as range rings; orbiting
 * shows they are nested spheres.
 */

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

import type { Guess } from "../api";
import { Centre } from "./Centre";
import { FitToViewport } from "./FitToViewport";
import { Guesses } from "./Guesses";
import { Hypothesis } from "./Hypothesis";
import { Shells } from "./Shells";
import { COLOR, MIN_DISTANCE, START_DISTANCE } from "./theme";

export function Board({
  guesses,
  answer,
  hypothesis,
}: {
  guesses: Guess[];
  answer: string | null;
  hypothesis: [number, number, number] | null;
}) {
  return (
    <Canvas
      camera={{ position: [0, START_DISTANCE, 0.01], fov: 46, near: 0.1, far: 300 }}
      dpr={[1, 2]}
      gl={{ antialias: true }}
    >
      <color attach="background" args={[COLOR.field]} />

      <FitToViewport />
      <Shells />
      <Hypothesis direction={hypothesis} />
      <Guesses guesses={guesses} answer={answer} />
      <Centre answer={answer} />

      <OrbitControls
        enablePan={false}
        minDistance={MIN_DISTANCE}
        maxDistance={START_DISTANCE}
        rotateSpeed={0.55}
        zoomSpeed={0.8}
        makeDefault
      />
    </Canvas>
  );
}
