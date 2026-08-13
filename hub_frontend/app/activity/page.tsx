import { ActivityTimeline } from "@/components/features/activity-timeline";

export const metadata = {
  title: "Activity | Cat Sentinell",
};

export default function ActivityPage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">Activity</h1>
        <p className="text-sm text-zinc-500">
          A running timeline of detections, frame entries, and alerts across every cat.
        </p>
      </header>
      <ActivityTimeline />
    </div>
  );
}
