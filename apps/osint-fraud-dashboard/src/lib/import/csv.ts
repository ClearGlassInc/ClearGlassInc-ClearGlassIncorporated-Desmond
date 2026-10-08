// RFC 4180 CSV parser: quoted fields, doubled quotes, embedded newlines,
// CRLF or LF line endings, optional UTF-8 BOM. Returns rows with the line
// number each row started on, so errors can point at the file.

export interface CsvRow {
  line: number;
  cells: string[];
}

export class CsvError extends Error {
  constructor(
    message: string,
    readonly line: number,
  ) {
    super(`line ${line}: ${message}`);
  }
}

export function parseCsv(input: string): CsvRow[] {
  const text = input.startsWith("﻿") ? input.slice(1) : input;
  const rows: CsvRow[] = [];
  let cells: string[] = [];
  let field = "";
  let inQuotes = false;
  let fieldStarted = false;
  let line = 1;
  let rowLine = 1;

  const endField = () => {
    cells.push(field);
    field = "";
    fieldStarted = false;
  };
  const endRow = () => {
    endField();
    // Skip fully empty lines.
    if (!(cells.length === 1 && cells[0] === "")) rows.push({ line: rowLine, cells });
    cells = [];
  };

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
          const next = text[i + 1];
          if (next !== undefined && next !== "," && next !== "\n" && next !== "\r") {
            throw new CsvError("unexpected character after closing quote", line);
          }
        }
      } else {
        if (ch === "\n") line++;
        field += ch;
      }
      continue;
    }
    if (ch === '"') {
      if (fieldStarted || field.length > 0) throw new CsvError("quote inside an unquoted field", line);
      inQuotes = true;
      fieldStarted = true;
    } else if (ch === ",") {
      endField();
    } else if (ch === "\r") {
      if (text[i + 1] === "\n") i++;
      endRow();
      line++;
      rowLine = line;
    } else if (ch === "\n") {
      endRow();
      line++;
      rowLine = line;
    } else {
      field += ch;
      fieldStarted = true;
    }
  }
  if (inQuotes) throw new CsvError("unterminated quoted field", rowLine);
  if (field.length > 0 || fieldStarted || cells.length > 0) endRow();
  return rows;
}
