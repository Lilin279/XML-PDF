"""MathML to HTML conversion for WeasyPrint PDF rendering.

WeasyPrint doesn't natively support MathML. This module provides
strategies to convert MathML into renderable HTML:

1. Unicode/HTML conversion for simple formulas (primary)
2. CSS-styled MathML passthrough (fallback)
3. SVG rendering via XSLT transform (future enhancement)

The converter walks the MathML tree and produces equivalent HTML
with Unicode characters and CSS styling.
"""

import re
from html import escape
from lxml import etree

# MathML namespace
MATHML_NS = 'http://www.w3.org/1998/Math/MathML'

# Unicode mappings for common math symbols
UNICODE_MAP = {
    # Greek letters (lowercase from MathML mi with mathvariant)
    'α': 'α', 'β': 'β', 'γ': 'γ', 'δ': 'δ',
    'ε': 'ε', 'ζ': 'ζ', 'η': 'η', 'θ': 'θ',
    'ι': 'ι', 'κ': 'κ', 'λ': 'λ', 'μ': 'μ',
    'ν': 'ν', 'ξ': 'ξ', 'ο': 'ο', 'π': 'π',
    'ρ': 'ρ', 'σ': 'σ', 'τ': 'τ', 'υ': 'υ',
    'φ': 'φ', 'χ': 'χ', 'ψ': 'ψ', 'ω': 'ω',
    # Greek uppercase (fallthrough)
    'Γ': 'Γ', 'Δ': 'Δ', 'Θ': 'Θ', 'Λ': 'Λ',
    'Ξ': 'Ξ', 'Π': 'Π', 'Σ': 'Σ', 'Φ': 'Φ',
    'Ψ': 'Ψ', 'Ω': 'Ω',
}

# Operator mappings
OPERATOR_MAP = {
    '×': '×', '÷': '÷', '±': '±', '∓': '∓',
    '≤': '≤', '≥': '≥', '≠': '≠',
    '≈': '≈', '≡': '≡', '∼': '∼',
    '<': '<', '>': '>', '=': '=',
    '+': '+', '−': '−', '*': '·', '/': '/',
    '∑': '∑', '∏': '∏', '∫': '∫',
    '√': '√', '∂': '∂', '∞': '∞',
    '→': '→', '⇒': '⇒', '↔': '↔',
    '∧': '∧', '∨': '∨', '¬': '¬',
    '∈': '∈', '∉': '∉', '⊂': '⊂',
    '∩': '∩', '∪': '∪',
    '′': '′', '″': '″',
    # Function names
    'exp': 'exp', 'log': 'log', 'ln': 'ln', 'sin': 'sin',
    'cos': 'cos', 'tan': 'tan', 'lim': 'lim',
}


def mathml_to_html(mathml_str: str, is_inline: bool = True) -> str:
    """Convert a MathML XML string to HTML for WeasyPrint rendering.

    This is the main entry point. It uses a recursive walker to
    convert MathML elements into HTML with Unicode characters.

    Args:
        mathml_str: Raw MathML XML string (e.g., <mml:math>...</mml:math>).
        is_inline: True for inline formulas, False for display formulas.

    Returns:
        HTML string suitable for embedding in the document,
        e.g., '<span class="math-inline">p = exp(...)/...</span>'.
    """
    # Clean up the MathML string
    mathml_str = mathml_str.strip()

    # Remove namespace prefixes for parsing
    cleaned = mathml_str.replace('mml:', '')

    try:
        root = etree.fromstring(cleaned.encode('utf-8'))
    except etree.XMLSyntaxError:
        # If parsing fails, return a cleaned text version
        return f'<span class="math-inline math-fallback">{_fallback_text(mathml_str)}</span>'

    result = _walk_mathml(root)

    wrapper_class = 'math-inline' if is_inline else 'math-display'
    return f'<span class="{wrapper_class}">{result}</span>'


def _walk_mathml(el) -> str:
    """Recursively walk a MathML element and produce HTML."""
    tag = etree.QName(el).localname if hasattr(el, 'tag') else ''

    if tag == 'math':
        parts = []
        if el.text and el.text.strip():
            parts.append(escape(el.text.strip()))
        for child in el:
            parts.append(_walk_mathml(child))
            if child.tail and child.tail.strip():
                parts.append(escape(child.tail.strip()))
        return ''.join(parts)

    elif tag == 'mrow':
        parts = []
        if el.text and el.text.strip():
            parts.append(escape(el.text.strip()))
        for child in el:
            parts.append(_walk_mathml(child))
            if child.tail and child.tail.strip():
                parts.append(escape(child.tail.strip()))
        return ''.join(parts)

    elif tag == 'mfrac':
        children = list(el)
        num = _walk_mathml(children[0]) if len(children) > 0 else ''
        den = _walk_mathml(children[1]) if len(children) > 1 else ''
        return f'<span class="math-frac"><span class="math-frac-num">{num}</span><span class="math-frac-den">{den}</span></span>'

    elif tag == 'msup':
        base = _walk_mathml(el[0]) if len(el) > 0 else ''
        sup = _walk_mathml(el[1]) if len(el) > 1 else ''
        return f'{base}<sup>{sup}</sup>'

    elif tag == 'msub':
        base = _walk_mathml(el[0]) if len(el) > 0 else ''
        sub = _walk_mathml(el[1]) if len(el) > 1 else ''
        return f'{base}<sub>{sub}</sub>'

    elif tag == 'msubsup':
        base = _walk_mathml(el[0]) if len(el) > 0 else ''
        sub = _walk_mathml(el[1]) if len(el) > 1 else ''
        sup = _walk_mathml(el[2]) if len(el) > 2 else ''
        return f'{base}<sub>{sub}</sub><sup>{sup}</sup>'

    elif tag == 'mover':
        base = _walk_mathml(el[0]) if len(el) > 0 else ''
        over = _walk_mathml(el[1]) if len(el) > 1 else ''
        return f'<span class="math-over">{over}</span>{base}'

    elif tag == 'munder':
        base = _walk_mathml(el[0]) if len(el) > 0 else ''
        under = _walk_mathml(el[1]) if len(el) > 1 else ''
        return f'<span class="math-under">{under}</span>{base}'

    elif tag == 'mi':
        text = _get_text(el)
        # Check for Greek letters or special identifiers
        var = text.strip()
        if var in UNICODE_MAP:
            return UNICODE_MAP[var]
        if len(var) <= 2:
            return f'<i>{escape(var)}</i>'
        return escape(var)

    elif tag == 'mn':
        text = _get_text(el)
        return escape(text.strip())

    elif tag == 'mo':
        text = _get_text(el).strip()
        if text in OPERATOR_MAP:
            return OPERATOR_MAP[text]
        if text in ('⁡', '⁣', '⁢'):  # FUNCTION APPLICATION, INVISIBLE TIMES, INVISIBLE SEPARATOR
            return ''
        if text == '∗' or text == '∗':  # ASTERISK OPERATOR
            return '·'
        if text == '−' or text == '−':  # MINUS SIGN
            return '−'
        if text in ('(', ')', '[', ']', '{', '}'):
            return escape(text)
        if text in ('=', '+', '<', '>', '/'):
            return f' {escape(text)} '
        # For other operators, be conservative with spacing
        return escape(text)

    elif tag == 'mtext':
        text = _get_text(el)
        # Remove non-breaking spaces
        text = text.replace(' ', ' ')
        return escape(text.strip())

    elif tag == 'mspace':
        return ' '

    elif tag == 'mroot':
        children = list(el)
        base = _walk_mathml(children[0]) if len(children) > 0 else ''
        return f'<span class="math-root">√{base}</span>'

    elif tag == 'msqrt':
        children = list(el)
        inner = ''.join(_walk_mathml(c) for c in children)
        return f'<span class="math-sqrt">√({inner})</span>'

    elif tag == 'mtable':
        # Matrix/array
        parts = []
        for child in el:
            parts.append(_walk_mathml(child))
        return f'<span class="math-matrix">[{"|".join(parts)}]</span>'

    elif tag == 'mtr':
        parts = []
        for child in el:
            parts.append(_walk_mathml(child))
        return ', '.join(parts)

    elif tag == 'mtd':
        parts = []
        for child in el:
            parts.append(_walk_mathml(child))
        return ''.join(parts)

    else:
        # Default: recurse and combine text
        parts = []
        if el.text and el.text.strip():
            parts.append(escape(el.text.strip()))
        for child in el:
            parts.append(_walk_mathml(child))
            if child.tail and child.tail.strip():
                parts.append(escape(child.tail.strip()))
        return ''.join(parts)


def _get_text(el) -> str:
    """Get all text content from a MathML element."""
    return ''.join(el.itertext())


def _fallback_text(mathml_str: str) -> str:
    """Extract a plain-text fallback from malformed MathML."""
    # Strip XML tags
    text = re.sub(r'<[^>]+>', ' ', mathml_str)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return escape(text) if text else "[Formula]"
