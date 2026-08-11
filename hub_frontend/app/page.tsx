import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-8 text-center">
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Cat Sentinel Hub</h1>
        <p className="mt-2 max-w-md text-zinc-500">
          Dashboard for the live annotated camera feed and active cat
          trackers.
        </p>
      </div>
      <Link
        href="/live"
        className="rounded-md bg-zinc-100 px-5 py-2.5 text-sm font-medium text-zinc-900 transition-colors hover:bg-white"
      >
        Go to Live Feed
      </Link>
    </div>
  );
}
