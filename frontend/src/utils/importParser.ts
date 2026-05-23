export interface ParsedLine {
  email: string;
  password: string;
  client_id: string;
  refresh_token: string;
}

export interface ParseError {
  line_number: number;
  content: string;
  reason: string;
}

export interface ParseResult {
  valid: ParsedLine[];
  errors: ParseError[];
}

export function parseImportText(text: string): ParseResult {
  const valid: ParsedLine[] = [];
  const errors: ParseError[] = [];

  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    let parts: string[];
    if (line.includes('----')) {
      parts = line.split('----').map(p => p.trim());
    } else {
      parts = line.split(/\s+/);
    }

    if (parts.length !== 4) {
      errors.push({
        line_number: i + 1,
        content: line,
        reason: `字段数量不足（期望 4 个字段，实际 ${parts.length} 个）`,
      });
    } else {
      valid.push({
        email: parts[0],
        password: parts[1],
        client_id: parts[2],
        refresh_token: parts[3],
      });
    }
  }

  return { valid, errors };
}
