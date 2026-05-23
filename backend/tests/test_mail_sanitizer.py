from app.services.mail_sanitizer import sanitize_html


class TestSanitizeHtml:
    def test_removes_script_tags(self):
        html = '<p>Hello</p><script>alert("xss")</script>'
        assert "<script>" not in sanitize_html(html)
        assert "Hello" in sanitize_html(html)

    def test_removes_iframe(self):
        html = '<iframe src="http://evil.com"></iframe><p>OK</p>'
        result = sanitize_html(html)
        assert "<iframe" not in result
        assert "OK" in result

    def test_removes_event_handlers(self):
        html = '<div onclick="steal()">Click</div>'
        result = sanitize_html(html)
        assert "onclick" not in result
        assert "Click" in result

    def test_preserves_safe_html(self):
        html = '<h1>Title</h1><p>Body with <strong>bold</strong> and <a href="https://example.com">link</a></p>'
        result = sanitize_html(html)
        assert "<h1>" in result
        assert "<strong>" in result
        assert 'href="https://example.com"' in result

    def test_adds_safe_link_attributes(self):
        html = '<a href="https://example.com">Link</a>'
        result = sanitize_html(html)
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_removes_javascript_href(self):
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_html(html)
        assert "javascript:" not in result

    def test_preserves_img_tags(self):
        html = '<img src="https://example.com/img.png" alt="photo">'
        result = sanitize_html(html)
        assert "<img" in result
        assert 'src="https://example.com/img.png"' in result

    def test_empty_input(self):
        assert sanitize_html("") == ""
