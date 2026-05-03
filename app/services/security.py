"""
Security utilities - XSS sanitization and input validation.
"""
import bleach
from bleach.css_sanitizer import CSSSanitizer


ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code',
    'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'i', 'img', 'li', 'ol', 'p', 'pre', 'span', 'strong',
    'sub', 'sup', 'ul', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
}


def sanitize_html(text):
    """Sanitize HTML to prevent XSS attacks while allowing safe tags."""
    if not text:
        return text
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )


def sanitize_text(text, max_length=None):
    """Sanitize plain text - strip HTML and limit length."""
    if not text:
        return text
    # Strip all HTML tags
    clean = bleach.clean(text, tags=[], strip=True)
    if max_length and len(clean) > max_length:
        clean = clean[:max_length]
    return clean.strip()