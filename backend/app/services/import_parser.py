from dataclasses import dataclass


@dataclass
class ParsedMailbox:
    email: str
    password: str
    client_id: str
    refresh_token: str


@dataclass
class ImportError:
    line_number: int
    content: str
    reason: str


@dataclass
class ParseResult:
    valid: list[ParsedMailbox]
    errors: list[ImportError]


def _parse_line(line: str) -> ParsedMailbox | None:
    if "----" in line:
        parts = [p.strip() for p in line.split("----")]
    else:
        parts = line.split()

    if len(parts) != 4:
        return None

    return ParsedMailbox(
        email=parts[0].strip(),
        password=parts[1].strip(),
        client_id=parts[2].strip(),
        refresh_token=parts[3].strip(),
    )


def parse_import_text(text: str) -> ParseResult:
    valid: list[ParsedMailbox] = []
    errors: list[ImportError] = []

    for line_num, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parsed = _parse_line(line)
        if parsed is None:
            field_count = len(line.split("----")) if "----" in line else len(line.split())
            errors.append(ImportError(
                line_number=line_num,
                content=line,
                reason=f"字段数量不足（期望 4 个字段，实际 {field_count} 个）",
            ))
        else:
            valid.append(parsed)

    return ParseResult(valid=valid, errors=errors)
