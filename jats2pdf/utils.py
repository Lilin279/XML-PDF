"""Utility functions for JATS2PDF."""

import re
from typing import Optional


def format_vancouver(citation) -> str:
    """Format a ReferenceCitation into Vancouver style text.

    Journal: Authors. Title. Journal Abbrev. Year; Volume: Pages.
    Book: Authors. Title. Edition. Publisher Location: Publisher; Year.
    Web: Authors. Title. URL. Date accessed.

    Args:
        citation: A ReferenceCitation object.

    Returns:
        Formatted reference string in Vancouver style.
    """
    parts = []

    # Authors
    if citation.authors:
        authors_str = _format_authors(citation.authors)
        parts.append(authors_str)

    # Title
    if citation.article_title:
        parts.append(f"{citation.article_title}.")

    # Source
    if citation.source:
        parts.append(citation.source)

    # Edition (for books)
    if citation.edition:
        parts.append(f"{citation.edition} edn.")

    # Year
    if citation.year:
        parts.append(citation.year)

    # Volume and pages (for journals)
    if citation.volume:
        vol_str = citation.volume
        if citation.first_page:
            vol_str += f": {citation.first_page}"
            if citation.last_page:
                vol_str += f"-{citation.last_page}"
        parts.append(vol_str)
    elif citation.first_page:
        pages = citation.first_page
        if citation.last_page:
            pages += f"-{citation.last_page}"
        parts.append(pages)

    # Publisher info (for books)
    if citation.publisher_name:
        publisher = citation.publisher_name
        if citation.publisher_loc:
            publisher = f"{citation.publisher_loc}: {publisher}"
        parts.append(publisher)

    # Comment / date accessed (for web)
    if citation.date_in_citation:
        parts.append(citation.date_in_citation)

    # DOI
    if citation.doi:
        parts.append(citation.doi)

    # Join with periods
    result = ""
    for i, part in enumerate(parts):
        if i == 0:
            result = part
        elif i == 1 and citation.publication_type == 'journal':
            result += f". {part}"
        elif part.startswith('http') or part.startswith('doi'):
            result += f" {part}"
        elif part.startswith('('):
            result += f" {part}"
        else:
            result += f". {part}"

    return result


def _format_authors(authors: list) -> str:
    """Format author list in Vancouver style.

    Args:
        authors: List of author name strings like "Surname GN".

    Returns:
        Formatted author string.
    """
    if not authors:
        return ""

    formatted = []
    for author in authors:
        if author.lower() == 'et al.':
            formatted.append('et al.')
            continue

        parts = author.split()
        if len(parts) >= 2:
            surname = parts[0]
            initials = ''.join(p[0] for p in parts[1:])
            formatted.append(f"{surname} {initials}")
        else:
            formatted.append(author)

    if len(formatted) > 6:
        formatted = formatted[:6] + ['et al.']

    return ', '.join(formatted)


def format_date(day: str = "", month: str = "", year: str = "") -> str:
    """Format a date from day/month/year components.

    Args:
        day: Day of month (optional).
        month: Month number (optional).
        year: Year (optional).

    Returns:
        Formatted date string.
    """
    month_names = {
        '1': 'January', '2': 'February', '3': 'March',
        '4': 'April', '5': 'May', '6': 'June',
        '7': 'July', '8': 'August', '9': 'September',
        '10': 'October', '11': 'November', '12': 'December',
    }
    month_name = month_names.get(month, month)

    parts = []
    if day:
        parts.append(day)
    if month_name:
        parts.append(month_name)
    if year:
        parts.append(year)

    return ' '.join(parts)


def format_history_date(dates: list) -> dict:
    """Format history dates (received, revised, accepted).

    Args:
        dates: List of HistoryDate objects.

    Returns:
        Dict with 'received', 'revised', 'accepted' as formatted date strings.
    """
    result = {}
    for d in dates:
        formatted = format_date(d.day, d.month, d.year)
        if d.date_type == 'received':
            result['received'] = formatted
        elif d.date_type == 'rev-recd':
            result['revised'] = formatted
        elif d.date_type == 'accepted':
            result['accepted'] = formatted
    return result


def section_number_from_id(sec_id: str) -> str:
    """Extract section number from section ID.

    JATS section IDs follow patterns like:
    - 'S1' -> '1'
    - 'S2.SS1' -> '2.1'
    - 'S2.SS3.SSS1' -> '2.3.1'

    Args:
        sec_id: Section ID string.

    Returns:
        Section number string.
    """
    if not sec_id:
        return ""

    # Pattern: S{num}, SS{num}, SSS{num}
    numbers = []
    for part in sec_id.split('.'):
        match = re.match(r'S+(\d+)', part, re.IGNORECASE)
        if match:
            numbers.append(match.group(1))

    return '.'.join(numbers)


def extract_doi(article_ids: list) -> str:
    """Extract DOI from list of ArticleId objects.

    Args:
        article_ids: List of ArticleId objects.

    Returns:
        DOI value string, or empty string.
    """
    for aid in article_ids:
        if aid.id_type == 'doi':
            return aid.value
    return ""


def extract_issn(issns: list, pub_type: str = 'ppub') -> str:
    """Extract ISSN of a specific publication type.

    Args:
        issns: List of ISSN objects.
        pub_type: 'ppub' or 'epub'.

    Returns:
        ISSN value string, or empty string.
    """
    for issn in issns:
        if issn.pub_type == pub_type:
            return issn.value
    return ""


def extract_epub_date(pub_dates: list):
    """Extract the epub publication date.

    Args:
        pub_dates: List of PubDate objects.

    Returns:
        PubDate for epub type, or first available.
    """
    for pd in pub_dates:
        if pd.pub_type == 'epub':
            return pd
    return pub_dates[0] if pub_dates else None
