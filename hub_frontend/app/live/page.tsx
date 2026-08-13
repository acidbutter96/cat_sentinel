import { LiveVideoFeed } from "@/components/features/live-video-feed";
import { TrackerList } from "@/components/features/tracker-list";

export const metadata = {
  title: "Live Feed | Cat Sentinell",
};

export default function LivePage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">Live Feed</h1>
        <p className="text-sm text-zinc-500">
          Direct camera stream and currently tracked cats with their latest snapshots.
        </p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <LiveVideoFeed />
        <aside className="min-h-[300px] lg:min-h-0">
          <TrackerList />
        </aside>
      </div>
    </div>
  );
}
