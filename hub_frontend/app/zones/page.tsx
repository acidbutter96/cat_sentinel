import { ZoneEditor } from "@/components/features/zone-editor";

export const metadata = {
  title: "Danger Zones | Cat Sentinell",
};

export default function ZonesPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">Danger Zones</h1>
        <p className="text-sm text-zinc-500">
          Click on the frame to draw an area. Cat Sentinell alerts you when a cat&apos;s
          centroid enters it.
        </p>
      </header>
      <ZoneEditor />
    </div>
  );
}
