import { AlertHistory } from "@/components/features/alert-history";

export const metadata = {
  title: "Alerts | Cat Sentinell",
};

export default function AlertsPage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">Alerts</h1>
        <p className="text-sm text-zinc-500">
          Every time a cat entered the camera&apos;s view or a danger zone. Updates every few
          seconds.
        </p>
      </header>
      <AlertHistory />
    </div>
  );
}
