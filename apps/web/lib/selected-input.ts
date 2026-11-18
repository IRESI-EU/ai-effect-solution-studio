export const CSV_INPUT_KEY = "$ai_effect_input";
export function selectedCsv(value: any): { name: string; content: string } | null {
  const file = value?.[CSV_INPUT_KEY];
  return file?.schema_version === "1.0" && file.kind === "inline_csv"
    && typeof file.name === "string" && typeof file.content === "string" ? file : null;
}
export function csvInput(name: string, content: string) {
  const value = { [CSV_INPUT_KEY]: { schema_version: "1.0", kind: "inline_csv", name, content } };
  if (!name || name.length > 128 || /[/\\\0\r\n]/.test(name)) throw new Error("Select a CSV with a simple file name of at most 128 characters.");
  if (!content || new TextEncoder().encode(content).length > 60_000 || new TextEncoder().encode(JSON.stringify(value)).length > 65_536) {
    throw new Error("Select a UTF-8 CSV with at most 60,000 bytes.");
  }
  return value;
}
