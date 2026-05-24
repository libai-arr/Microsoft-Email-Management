import re

import bleach
from bleach.css_sanitizer import CSSSanitizer


ALLOWED_TAGS = [
    "a", "abbr", "acronym", "b", "blockquote", "br", "center",
    "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "small", "span",
    "strong", "style", "sub", "sup", "table", "tbody", "td", "th", "thead",
    "tr", "u", "ul",
]

ALLOWED_CSS_PROPERTIES = [
    "background", "background-color", "background-image", "background-position",
    "background-repeat", "background-size",
    "border", "border-bottom", "border-bottom-color", "border-bottom-style",
    "border-bottom-width", "border-collapse", "border-color", "border-left",
    "border-left-color", "border-left-style", "border-left-width", "border-radius",
    "border-right", "border-right-color", "border-right-style", "border-right-width",
    "border-spacing", "border-style", "border-top", "border-top-color",
    "border-top-style", "border-top-width", "border-width",
    "box-sizing", "clear", "color", "cursor", "direction", "display",
    "float", "font", "font-family", "font-size", "font-style", "font-variant",
    "font-weight", "height", "letter-spacing", "line-height",
    "list-style", "list-style-type",
    "margin", "margin-bottom", "margin-left", "margin-right", "margin-top",
    "max-height", "max-width", "min-height", "min-width",
    "opacity", "overflow", "overflow-x", "overflow-y",
    "padding", "padding-bottom", "padding-left", "padding-right", "padding-top",
    "table-layout", "text-align", "text-decoration", "text-indent", "text-overflow",
    "text-transform", "unicode-bidi", "vertical-align", "visibility",
    "white-space", "width", "word-break", "word-wrap",
]

CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)

ALLOWED_ATTRIBUTES = {
    "*": ["class", "style"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(html: str) -> str:
    if not html:
        return ""

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        css_sanitizer=CSS_SANITIZER,
    )

    # Strip existing target/rel to avoid duplicates, then add safe defaults
    cleaned = re.sub(r'\s*target\s*=\s*"[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*rel\s*=\s*"[^"]*"', '', cleaned)
    cleaned = re.sub(
        r'<a\s',
        '<a target="_blank" rel="noopener noreferrer" ',
        cleaned,
    )

    return cleaned
