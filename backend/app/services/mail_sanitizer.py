import re

import bleach


ALLOWED_TAGS = [
    "a", "abbr", "acronym", "b", "blockquote", "br", "center",
    "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "small", "span",
    "strong", "sub", "sup", "table", "tbody", "td", "th", "thead",
    "tr", "u", "ul",
]

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
    )

    cleaned = re.sub(
        r'<a\s',
        '<a target="_blank" rel="noopener noreferrer" ',
        cleaned,
    )

    return cleaned
