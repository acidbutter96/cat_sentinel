"use client";

import { useCallback, useState } from "react";

// Default to the same-origin proxy so the browser never needs to know the
// hub's real address. Can be overridden client-side to point straight at a
// different feed source.
const DEFAULT_STREAM_URL = "/api/stream";
const STREAM_URL = process.env.NEXT_PUBLIC_STREAM_URL || DEFAULT_STREAM_URL;

type FeedStatus = "loading" | "ok" | "error";

function buildSrc(base: string, cacheBust: number) {
  const separator = base.includes("?") ? "&" : "?";
  return cacheBust === 0 ? base : `${base}${separator}retry=${cacheBust}`;
}

export function LiveVideoFeed() {
  const [status, setStatus] = useState<FeedStatus>("loading");
  const [cacheBust, setCacheBust] = useState(0);

  const handleError = useCallback(() => {
    setStatus("error");
  }, []);

  const handleLoad = useCallback(() => {
    setStatus("ok");
  }, []);

  const handleRetry = useCallback(() => {
    setStatus("loading");
    setCacheBust((n) => n + 1);
  }, []);

  const src = buildSrc(STREAM_URL, cacheBust);

  return (
    <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border border-zinc-800 bg-black">
      {status !== "error" && (
        // eslint-disable-next-line @next/next/no-img-element -- MJPEG multipart stream, not compatible with next/image
        <img
          key={cacheBust}
          src={src}
          alt="Live annotated camera feed"
          onError={handleError}
          onLoad={handleLoad}
          className="h-full w-full object-contain"
        />
      )}

      {status === "loading" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/40 text-sm text-zinc-300">
          Connecting to feed…
        </div>
      )}

      {status === "error" && (
        <div className="flex flex-col items-center gap-3 p-8 text-center text-zinc-300">
          <p className="text-sm">
            Feed unavailable. The camera stream could not be loaded.
          </p>
          <button
            type="button"
            onClick={handleRetry}
            className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-white"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

export default LiveVideoFeed;
