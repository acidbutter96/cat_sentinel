import Link from "next/link";

const SECTIONS = [
  {
    href: "/live",
    title: "Live Feed",
    description: "Low-latency camera stream with tracked cats shown alongside it.",
  },
  {
    href: "/zones",
    title: "Danger Zones",
    description: "Draw the areas on camera you want Cat Sentinell to treat as off-limits.",
  },
  {
    href: "/cats",
    title: "Cats",
    description: "Every cat identity recognized so far -- give each one a name.",
  },
  {
    href: "/alerts",
    title: "Alerts",
    description: "History of every camera-entry and danger-zone alert that's fired.",
  },
  {
    href: "/activity",
    title: "Activity",
    description: "A running timeline of detections, entries, and alerts across all cats.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center gap-10 p-8 text-center">
      <div className="flex flex-col items-center gap-3 pt-8">
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-300">
          Always watching
        </span>
        <h1 className="text-4xl font-bold text-zinc-100">Cat Sentinell</h1>
        <p className="max-w-xl text-zinc-500">
          Detects and names every cat that crosses your camera, records continuously in
          hourly chunks, and alerts you the instant a cat enters frame or wanders into a
          danger zone.
        </p>
      </div>

      <div className="grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-2">
        {SECTIONS.map((section) => (
          <Link
            key={section.href}
            href={section.href}
            className="group flex flex-col gap-1.5 rounded-lg border border-zinc-800 bg-zinc-950 p-5 transition-colors hover:border-amber-500/40 hover:bg-zinc-900"
          >
            <span className="font-semibold text-zinc-100 group-hover:text-amber-300">
              {section.title}
            </span>
            <span className="text-sm text-zinc-500">{section.description}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
