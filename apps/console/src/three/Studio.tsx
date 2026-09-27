import { ContactShadows, Environment, Lightformer } from '@react-three/drei';

/**
 * Photographic studio lighting built from light panels (no HDRI download, so it works offline and
 * behind strict CSPs): a large softbox overhead, two rim strips and a warm fill.
 */
export default function Studio({ shadowY = -1.2, warm = true }: { shadowY?: number; warm?: boolean }) {
  return (
    <>
      <ambientLight intensity={0.25} />
      <directionalLight position={[4, 6, 5]} intensity={1.4} castShadow />
      <Environment resolution={256} frames={1}>
        <Lightformer form="rect" intensity={3} position={[0, 5, -2]} scale={[10, 4, 1]} rotation-x={Math.PI / 2} />
        <Lightformer form="rect" intensity={2} position={[-5, 1, -1]} scale={[3, 8, 1]} rotation-y={Math.PI / 2} />
        <Lightformer form="rect" intensity={2} position={[5, 1, -1]} scale={[3, 8, 1]} rotation-y={-Math.PI / 2} />
        <Lightformer form="ring" intensity={warm ? 1.5 : 0.8} color={warm ? '#ffb454' : '#ffffff'} position={[0, 0, 6]} scale={3} />
      </Environment>
      <ContactShadows position={[0, shadowY, 0]} opacity={0.45} scale={14} blur={2.6} far={4} resolution={512} />
    </>
  );
}
