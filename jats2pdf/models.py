"""Data models for JATS XML elements."""

from dataclasses import dataclass, field
from typing import Optional, Union, List


# ── Inline Content (mixed content within paragraphs) ──

@dataclass
class InlineText:
    """Plain text node."""
    text: str


@dataclass
class InlineItalic:
    """Italic-formatted text."""
    children: List['InlineNode']


@dataclass
class InlineBold:
    """Bold-formatted text."""
    children: List['InlineNode']


@dataclass
class InlineSup:
    """Superscript text."""
    children: List['InlineNode']


@dataclass
class InlineSub:
    """Subscript text."""
    children: List['InlineNode']


@dataclass
class InlineXref:
    """Cross-reference to bibliography, table, or figure."""
    rid: str
    ref_type: str  # bibr, table, fig
    text: str = ""


@dataclass
class InlineFormula:
    """Inline mathematical formula (MathML as raw XML string)."""
    mathml: str  # Raw MathML XML string


@dataclass
class InlineBreak:
    """Line break within a paragraph/table cell."""
    pass


@dataclass
class InlineExtLink:
    """External hyperlink with href and display text."""
    href: str
    text: str = ""


@dataclass
class InlineGraphic:
    """Inline graphic/image within a paragraph or table cell."""
    href: str  # xlink:href


InlineNode = Union[InlineText, InlineItalic, InlineBold, InlineSup, InlineSub,
                   InlineXref, InlineFormula, InlineBreak, InlineExtLink,
                   InlineGraphic]


# ── Article Metadata ──

@dataclass
class JournalId:
    """Journal identifier."""
    id_type: str  # publisher-id, etc.
    value: str


@dataclass
class ISSN:
    """ISSN identifier."""
    pub_type: str  # ppub, epub
    value: str


@dataclass
class JournalMeta:
    """Journal metadata."""
    journal_id: str = ""
    journal_title: str = ""
    abbrev_journal_title: str = ""
    issns: List[ISSN] = field(default_factory=list)
    publisher: str = ""


@dataclass
class ArticleId:
    """Article identifier (DOI, publisher-id)."""
    id_type: str
    value: str


@dataclass
class PubDate:
    """Publication date."""
    pub_type: str  # epub, collection, etc.
    day: str = ""
    month: str = ""
    year: str = ""


@dataclass
class HistoryDate:
    """History date (received, revised, accepted)."""
    date_type: str
    day: str = ""
    month: str = ""
    year: str = ""


@dataclass
class Copyright:
    """Copyright and license information."""
    statement: str = ""
    year: str = ""
    license_text: str = ""
    license_href: str = ""
    license_nodes: Optional[List[InlineNode]] = field(default_factory=list)


@dataclass
class Author:
    """Article author."""
    surname: str = ""
    given_names: str = ""
    orcid: str = ""
    email: str = ""
    aff_refs: List[str] = field(default_factory=list)  # e.g., ['aff1', 'aff2']
    is_corresponding: bool = False
    corresp_id: str = ""


@dataclass
class Editor:
    """Academic editor."""
    surname: str = ""
    given_names: str = ""
    role: str = ""


@dataclass
class Affiliation:
    """Author affiliation."""
    id: str
    label: str  # Superscript label like "1", "2"
    text: str


@dataclass
class CorrespondingAuthor:
    """Corresponding author information."""
    id: str
    label: str  # Usually "*"
    emails: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)  # Author names


@dataclass
class AbstractSection:
    """A structured section within the abstract."""
    title: str
    paragraphs: List[List[InlineNode]] = field(default_factory=list)


@dataclass
class Abstract:
    """Article abstract."""
    sections: List[AbstractSection] = field(default_factory=list)


@dataclass
class KeywordGroup:
    """Group of keywords."""
    group_type: str  # author, etc.
    keywords: List[str] = field(default_factory=list)


# ── Front Matter ──

@dataclass
class FrontMatter:
    """Complete front matter of an article."""
    journal_meta: JournalMeta = field(default_factory=JournalMeta)
    article_type: str = ""
    article_ids: List[ArticleId] = field(default_factory=list)
    article_title: str = ""
    authors: List[Author] = field(default_factory=list)
    editors: List[Editor] = field(default_factory=list)
    affiliations: List[Affiliation] = field(default_factory=list)
    corresponding: Optional[CorrespondingAuthor] = None
    pub_dates: List[PubDate] = field(default_factory=list)
    volume: str = ""
    issue: str = ""
    elocation_id: str = ""
    history: List[HistoryDate] = field(default_factory=list)
    copyright: Optional[Copyright] = None
    abstract: Optional[Abstract] = None
    keywords: List[KeywordGroup] = field(default_factory=list)


# ── Body Elements ──

@dataclass
class TableCell:
    """A table cell."""
    content: List[InlineNode] = field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1
    style: str = ""  # Raw CSS style string
    align: str = "left"
    cell_type: str = "td"  # "td" or "th"


@dataclass
class TableRow:
    """A table row."""
    cells: List[TableCell] = field(default_factory=list)


@dataclass
class TableData:
    """Parsed table data."""
    headers: List[TableRow] = field(default_factory=list)
    body: List[TableRow] = field(default_factory=list)


@dataclass
class TableFootnote:
    """Footnote for a table."""
    id: str = ""
    paragraphs: List[List[InlineNode]] = field(default_factory=list)


@dataclass
class TableWrap:
    """Complete table wrapper (table + caption + footnotes)."""
    id: str = ""
    label: str = ""  # e.g., "Table 1."
    caption: List[List[InlineNode]] = field(default_factory=list)
    table: Optional[TableData] = None
    footnotes: List[TableFootnote] = field(default_factory=list)
    max_columns: int = 0  # Max column count across all rows (for landscape detection)


@dataclass
class Figure:
    """A figure with caption and graphic reference."""
    id: str = ""
    label: str = ""  # e.g., "Fig. 1."
    caption: List[List[InlineNode]] = field(default_factory=list)
    graphic_href: str = ""  # e.g., "RCM46777/fig1.jpg"
    graphic_id: str = ""


@dataclass
class Paragraph:
    """A paragraph with inline content."""
    id: str = ""
    content: List[InlineNode] = field(default_factory=list)


@dataclass
class Section:
    """A section of the article body or back matter."""
    id: str = ""
    title: str = ""
    sec_type: str = ""  # e.g., "data-availability", "COI-statement", etc.
    paragraphs: List[Paragraph] = field(default_factory=list)
    sections: List['Section'] = field(default_factory=list)
    tables: List[TableWrap] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    # Preserve original XML child order: ('p', obj) | ('table', obj) | etc.
    children_in_order: List = field(default_factory=list)


@dataclass
class Body:
    """Article body."""
    sections: List[Section] = field(default_factory=list)


# ── Back Matter ──

@dataclass
class ReferenceCitation:
    """A parsed reference/citation."""
    publication_type: str = "journal"  # journal, book, web
    authors: List[str] = field(default_factory=list)  # "Surname GN" format
    article_title: str = ""
    source: str = ""
    year: str = ""
    volume: str = ""
    first_page: str = ""
    last_page: str = ""
    doi: str = ""
    doi_href: str = ""
    edition: str = ""
    publisher_name: str = ""
    publisher_loc: str = ""
    comment: str = ""  # For web references
    date_in_citation: str = ""  # For web references (Accessed date)
    ext_link_href: str = ""  # For web references


@dataclass
class Reference:
    """A bibliographic reference."""
    id: str
    label: str  # e.g., "[1]"
    citation: Optional[ReferenceCitation] = None


@dataclass
class FootnoteGroup:
    """Group of footnotes (usually publisher notes)."""
    paragraphs: List[List[InlineNode]] = field(default_factory=list)


@dataclass
class SupplementaryMaterial:
    """Supplementary material reference."""
    id: str = ""
    href: str = ""
    label: str = ""


@dataclass
class BackMatter:
    """Complete back matter of an article."""
    sections: List[Section] = field(default_factory=list)
    acknowledgments: List[Paragraph] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    footnotes: List[FootnoteGroup] = field(default_factory=list)
    supplementary_materials: List[SupplementaryMaterial] = field(default_factory=list)


# ── Top-Level Article ──

@dataclass
class Article:
    """Complete JATS article."""
    front: FrontMatter = field(default_factory=FrontMatter)
    body: Body = field(default_factory=Body)
    back: BackMatter = field(default_factory=BackMatter)
    xml_path: str = ""  # Source XML file path (for figure path resolution)
