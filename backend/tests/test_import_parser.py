import pytest

from app.services.import_parser import parse_import_text, ImportError as ParseImportError


class TestParseImportText:
    def test_format_b_four_dashes(self):
        text = "alice@outlook.com----Pass123----abc-def----rt_token_abc"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert result.valid[0].email == "alice@outlook.com"
        assert result.valid[0].password == "Pass123"
        assert result.valid[0].client_id == "abc-def"
        assert result.valid[0].refresh_token == "rt_token_abc"
        assert len(result.errors) == 0

    def test_format_a_space_separated(self):
        text = "bob@outlook.com SecurePass jkl-mno rt_token_def"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert result.valid[0].email == "bob@outlook.com"

    def test_format_a_tab_separated(self):
        text = "bob@outlook.com\tSecurePass\tjkl-mno\trt_token_def"
        result = parse_import_text(text)
        assert len(result.valid) == 1

    def test_mixed_formats(self):
        text = "a@outlook.com----P1----C1----T1\nb@outlook.com P2 C2 T2"
        result = parse_import_text(text)
        assert len(result.valid) == 2
        assert len(result.errors) == 0

    def test_missing_fields_error(self):
        text = "bad@outlook.com onlypassword"
        result = parse_import_text(text)
        assert len(result.valid) == 0
        assert len(result.errors) == 1
        assert result.errors[0].line_number == 1

    def test_empty_lines_skipped(self):
        text = "\nalice@outlook.com----P----C----T\n\n"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert len(result.errors) == 0

    def test_multiple_errors_report_all_lines(self):
        text = "good@outlook.com----P----C----T\nbad1\nbad2 only"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert len(result.errors) == 2
        assert result.errors[0].line_number == 2
        assert result.errors[1].line_number == 3

    def test_whitespace_trimmed(self):
        text = "  alice@outlook.com----Pass----CID----Token  "
        result = parse_import_text(text)
        assert result.valid[0].email == "alice@outlook.com"
        assert result.valid[0].refresh_token == "Token"
