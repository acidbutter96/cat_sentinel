"use client";

import { useEffect, useState } from "react";
import type { Cat, CatSex } from "@/lib/types";

type FetchState = "loading" | "ok" | "error";

type CatDraft = {
  name: string;
  birth_date: string;
  sex: CatSex;
  description: string;
};

const emptyDraft: CatDraft = { name: "", birth_date: "", sex: "unknown", description: "" };

function draftFromCat(cat: Cat): CatDraft {
  return {
    name: cat.name,
    birth_date: cat.birth_date ?? "",
    sex: cat.sex,
    description: cat.description ?? "",
  };
}

function payloadFromDraft(draft: CatDraft) {
  return {
    name: draft.name.trim(),
    birth_date: draft.birth_date || null,
    sex: draft.sex,
    description: draft.description.trim() || null,
  };
}

export function CatList() {
  const [cats, setCats] = useState<Cat[]>([]);
  const [state, setState] = useState<FetchState>("loading");
  const [draft, setDraft] = useState<CatDraft>(emptyDraft);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetch("/api/cats", { cache: "no-store" });
        if (!response.ok) throw new Error();
        const data: unknown = await response.json();
        if (!cancelled) {
          setCats(Array.isArray(data) ? (data as Cat[]) : []);
          setState("ok");
        }
      } catch {
        if (!cancelled) setState("error");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  function setField<K extends keyof CatDraft>(field: K, value: CatDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    const payload = payloadFromDraft(draft);
    if (!payload.name) {
      setError("Name is required.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const response = await fetch(editingId ? `/api/cats/${editingId}` : "/api/cats", {
        method: editingId ? "PATCH" : "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error();
      let saved: Cat = await response.json();
      for (const imageFile of imageFiles) {
        const upload = await fetch(`/api/cats/${saved.id}/images`, {
          method: "POST",
          headers: { "content-type": imageFile.type },
          body: imageFile,
        });
        if (!upload.ok) throw new Error();
        saved = await upload.json();
      }
      setCats((current) =>
        editingId ? current.map((cat) => (cat.id === saved.id ? saved : cat)) : [...current, saved],
      );
      setDraft(emptyDraft);
      setImageFiles([]);
      setEditingId(null);
    } catch {
      setError("Could not save the cat profile.");
    } finally {
      setSaving(false);
    }
  }

  function edit(cat: Cat) {
    setEditingId(cat.id);
    setDraft(draftFromCat(cat));
    setImageFiles([]);
    setError(null);
  }

  function cancel() {
    setEditingId(null);
    setDraft(emptyDraft);
    setImageFiles([]);
    setError(null);
  }

  if (state === "loading") return <p className="text-sm text-zinc-500">Loading profiles…</p>;
  if (state === "error") return <p className="text-sm text-red-400">Couldn&apos;t reach the cats service.</p>;

  return (
    <div className="flex flex-col gap-5">
      <section className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
        <h2 className="text-base font-semibold text-zinc-100">
          {editingId ? "Edit registered cat" : "Register a cat"}
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <input
            value={draft.name}
            onChange={(event) => setField("name", event.target.value)}
            placeholder="Name"
            className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"
          />
          <select
            value={draft.sex}
            onChange={(event) => setField("sex", event.target.value as CatSex)}
            className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"
          >
            <option value="unknown">Sex unknown</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
          <input
            type="date"
            value={draft.birth_date}
            onChange={(event) => setField("birth_date", event.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"
          />
          <textarea
            value={draft.description}
            onChange={(event) => setField("description", event.target.value)}
            placeholder="Description"
            className="min-h-20 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 sm:col-span-2"
          />
          <label className="text-sm text-zinc-300 sm:col-span-2">
            Reference images (JPEG, PNG, or WebP; max. 5 MB each)
            <input
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => setImageFiles(Array.from(event.target.files ?? []))}
              className="mt-1 block w-full text-sm text-zinc-400"
            />
          </label>
        </div>
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            disabled={saving}
            onClick={save}
            className="rounded-md bg-amber-500 px-3 py-2 text-sm font-semibold text-zinc-950 disabled:opacity-50"
          >
            {saving ? "Saving…" : editingId ? "Save changes" : "Register cat"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={cancel}
              className="rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-300"
            >
              Cancel
            </button>
          )}
        </div>
      </section>

      {cats.length === 0 ? (
        <p className="text-sm text-zinc-500">No registered cats yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {cats.map((cat) => (
            <li key={cat.id} className="flex items-start justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <div className="flex gap-3">
                {cat.photo_path && (
                  // eslint-disable-next-line @next/next/no-img-element -- local dynamic profile image
                  <img
                    src={`/api/cats/${cat.id}/photo?v=${encodeURIComponent(cat.photo_path)}`}
                    alt={cat.name}
                    className="h-16 w-16 rounded-full object-cover"
                  />
                )}
                <div>
                <p className="font-medium text-zinc-100">{cat.name}</p>
                <p className="text-xs text-zinc-500">
                  {cat.sex} · {cat.birth_date ?? "birth date unknown"}
                </p>
                {cat.description && <p className="mt-2 text-sm text-zinc-300">{cat.description}</p>}
                </div>
              </div>
              <button
                type="button"
                onClick={() => edit(cat)}
                className="rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300"
              >
                Edit
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default CatList;
