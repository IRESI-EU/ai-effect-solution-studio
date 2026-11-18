"use client";
import { useEffect, useRef, useState } from "react";
import { csvInput, selectedCsv } from "../lib/selected-input";

export default function SelectedCsvInput({ value, onChange, disabled = false }: {
  value: unknown; onChange: (value: Record<string, unknown> | null) => void; disabled?: boolean;
}) {
  const [error, setError] = useState("");
  const selection = useRef(0);
  useEffect(() => () => { selection.current++; }, []);
  const saved = selectedCsv(value);
  return <div>
    <label htmlFor="selected-csv-file">Select CSV data</label>
    <input id="selected-csv-file" type="file" accept=".csv,text/csv" disabled={disabled} onChange={async event => {
      const attempt = ++selection.current;
      const file = event.currentTarget.files?.[0];
      setError("");
      if (!file) return;
      try {
        if (file.size > 60_000) throw new Error("Select a CSV with at most 60,000 bytes.");
        const bytes = await file.arrayBuffer();
        const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
        const next = csvInput(file.name, text);
        if (selection.current === attempt) onChange(next);
      } catch (failure) {
        if (selection.current === attempt) setError(failure instanceof Error ? failure.message : "Could not read the selected CSV.");
      }
    }} />
    {saved && <p>Selected data: <strong>{saved.name}</strong> <button type="button" disabled={disabled} onClick={() => { selection.current++; onChange(null); setError(""); }}>Remove CSV</button></p>}
    <p>UTF-8 CSV, up to 60,000 bytes, with column names and data rows. Save the solution before running. CSV contents stay out of AI requests.</p>
    {error && <p role="alert">{error}</p>}
  </div>;
}
