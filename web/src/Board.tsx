/**
 * The board, stage 4: deliberately unpolished.
 *
 * The hidden word sits at the centre. Each guess is a dot at the position
 * the server computed — distance from the centre is the score, direction is
 * meaning. Reference rings, labels, semantic zoom, the HUD and the win state
 * are stage 5.
 */

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { Guess } from "./api";

export function Board({ guesses }: { guesses: Guess[] }) {
  return (
    <Canvas camera={{ position: [0, 18, 0.001], fov: 50 }}>
      <ambientLight intensity={1.2} />
      <pointLight position={[10, 10, 10]} />

      {/* The hidden word: unknown until it is solved. */}
      <mesh>
        <sphereGeometry args={[0.35, 16, 16]} />
        <meshStandardMaterial color="#ffffff" wireframe />
      </mesh>

      {guesses.map((guess) => (
        <mesh
          key={guess.guess_number}
          position={[guess.position.x, guess.position.y, guess.position.z]}
        >
          <sphereGeometry args={[0.18, 12, 12]} />
          <meshStandardMaterial
            color={guess.is_best_so_far ? "#f1c40f" : "#3498db"}
          />
        </mesh>
      ))}

      <OrbitControls />
    </Canvas>
  );
}
