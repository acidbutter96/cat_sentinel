import { CatList } from "@/components/features/cat-list";

export const metadata = {
  title: "Cats | Cat Sentinell",
};

export default function CatsPage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-zinc-100">Cats</h1>
        <p className="text-sm text-zinc-500">
          Register known cats with name, birth date, sex, and description.
        </p>
      </header>
      <CatList />
    </div>
  );
}
