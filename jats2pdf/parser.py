"""JATS XML Parser using lxml — converts JATS XML to Python data objects."""

from lxml import etree
from typing import Optional, List
import re

from .models import (
    Article, FrontMatter, Body, BackMatter,
    JournalMeta, ISSN, ArticleId, PubDate, HistoryDate, Copyright,
    Author, Editor, Affiliation, CorrespondingAuthor,
    Abstract, AbstractSection, KeywordGroup,
    Section, Paragraph, TableWrap, TableData, TableRow, TableCell,
    TableFootnote, Figure, Reference, ReferenceCitation,
    FootnoteGroup, SupplementaryMaterial,
    InlineText, InlineItalic, InlineBold, InlineSup, InlineSub,
    InlineXref, InlineFormula, InlineBreak, InlineExtLink,
    InlineGraphic, InlineNode,
)

# Namespaces used in JATS XML
NSMAP = {
    'mml': 'http://www.w3.org/1998/Math/MathML',
    'xlink': 'http://www.w3.org/1999/xlink',
}


def _xpath(el, expr):
    """Run XPath with standard JATS namespaces."""
    return el.xpath(expr, namespaces=NSMAP)


def _text(el) -> str:
    """Get all text content of an element, including from children, with normalized whitespace."""
    if el is None:
        return ""
    result = ''.join(el.itertext())
    # Normalize whitespace for display
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def _tail(el) -> str:
    """Get tail text of an element."""
    if el is None or el.tail is None:
        return ""
    return el.tail


def _attr(el, name, default="") -> str:
    """Get attribute value safely."""
    if el is None:
        return default
    return el.get(name, default)


class JATSParser:
    """Parse JATS XML files into structured Article objects."""

    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        # Resolve entities and parse
        parser = etree.XMLParser(resolve_entities=True, no_network=True, huge_tree=True)
        self.tree = etree.parse(xml_path, parser=parser)
        self.root = self.tree.getroot()
        # Track section numbering
        self._section_numbers = []

    def parse(self) -> Article:
        """Parse the complete JATS XML into an Article object."""
        article = Article(xml_path=self.xml_path)
        article.front = self._parse_front()
        article.body = self._parse_body()
        article.back = self._parse_back()
        return article

    # ── Front Matter ──

    def _parse_front(self) -> FrontMatter:
        front_el = self.root.find('front')
        if front_el is None:
            return FrontMatter()

        fm = FrontMatter()

        # Journal metadata
        jm = front_el.find('journal-meta')
        if jm is not None:
            fm.journal_meta = self._parse_journal_meta(jm)

        # Article metadata
        am = front_el.find('article-meta')
        if am is not None:
            fm.article_type = self._parse_article_type(am)
            fm.article_ids = self._parse_article_ids(am)
            fm.article_title = self._parse_article_title(am)
            fm.authors, fm.editors = self._parse_contributors(am)
            fm.affiliations = self._parse_affiliations(am)
            fm.corresponding = self._parse_corresponding(am)
            fm.pub_dates = self._parse_pub_dates(am)
            fm.volume = _text(am.find('volume'))
            fm.issue = _text(am.find('issue'))
            fm.elocation_id = _text(am.find('elocation-id'))
            fm.history = self._parse_history(am)
            fm.copyright = self._parse_copyright(am)
            fm.abstract = self._parse_abstract(am)
            fm.keywords = self._parse_keywords(am)

        return fm

    def _parse_journal_meta(self, jm) -> JournalMeta:
        meta = JournalMeta()
        jid = jm.find('journal-id')
        if jid is not None:
            meta.journal_id = _text(jid)
        jtg = jm.find('journal-title-group')
        if jtg is not None:
            meta.journal_title = _text(jtg.find('journal-title'))
            # Get publisher abbreviation
            for ajt in jtg.findall('abbrev-journal-title'):
                if _attr(ajt, 'abbrev-type') == 'publisher':
                    meta.abbrev_journal_title = _text(ajt)
                    break
            if not meta.abbrev_journal_title:
                meta.abbrev_journal_title = _text(jtg.find('abbrev-journal-title'))
        for issn_el in jm.findall('issn'):
            meta.issns.append(ISSN(
                pub_type=_attr(issn_el, 'pub-type', ''),
                value=_text(issn_el)
            ))
        pub = jm.find('publisher/publisher-name')
        if pub is not None:
            meta.publisher = _text(pub)
        return meta

    def _parse_article_type(self, am) -> str:
        sc = am.find('article-categories/subj-group/subject')
        return _text(sc) if sc is not None else ""

    def _parse_article_ids(self, am) -> List[ArticleId]:
        ids = []
        for aid in am.findall('article-id'):
            ids.append(ArticleId(
                id_type=_attr(aid, 'pub-id-type', ''),
                value=_text(aid)
            ))
        return ids

    def _parse_article_title(self, am) -> str:
        title_el = am.find('title-group/article-title')
        return self._render_inline_to_text(title_el) if title_el is not None else ""

    def _parse_contributors(self, am) -> tuple:
        """Return (authors, editors) lists."""
        authors = []
        editors = []
        for cg in am.findall('contrib-group'):
            for contrib in cg.findall('contrib'):
                contrib_type = _attr(contrib, 'contrib-type', 'author')
                if contrib_type == 'editor':
                    editors.append(self._parse_editor(contrib))
                else:
                    authors.append(self._parse_author(contrib))
        return authors, editors

    def _parse_author(self, contrib) -> Author:
        author = Author()
        orcid_el = contrib.find('contrib-id[@contrib-id-type="orcid"]')
        if orcid_el is not None:
            author.orcid = _text(orcid_el)
        name_el = contrib.find('name')
        if name_el is not None:
            author.surname = _text(name_el.find('surname'))
            author.given_names = _text(name_el.find('given-names'))
        author.email = _text(contrib.find('email'))

        # Affiliation references
        for xref in contrib.findall('xref[@ref-type="aff"]'):
            rid = _attr(xref, 'rid', '')
            if rid:
                author.aff_refs.append(rid)

        # Corresponding author marker
        corresp_xref = contrib.find('xref[@ref-type="corresp"]')
        if corresp_xref is not None:
            author.is_corresponding = True
            author.corresp_id = _attr(corresp_xref, 'rid', '')

        return author

    def _parse_editor(self, contrib) -> Editor:
        editor = Editor()
        name_el = contrib.find('name')
        if name_el is not None:
            editor.surname = _text(name_el.find('surname'))
            editor.given_names = _text(name_el.find('given-names'))
        editor.role = _text(contrib.find('role'))
        return editor

    def _parse_affiliations(self, am) -> List[Affiliation]:
        affs = []
        for aff_el in am.findall('aff'):
            aff = Affiliation(
                id=_attr(aff_el, 'id', ''),
                label=_text(aff_el.find('sup')),
                text=''.join(aff_el.itertext()).strip()
            )
            # Clean up: remove the sup label from text
            if aff.label and aff.text.startswith(aff.label):
                aff.text = aff.text[len(aff.label):].strip()
            affs.append(aff)
        return affs

    def _parse_corresponding(self, am) -> Optional[CorrespondingAuthor]:
        an = am.find('author-notes')
        if an is None:
            return None
        corresp_el = an.find('corresp')
        if corresp_el is None:
            return None
        corr = CorrespondingAuthor(
            id=_attr(corresp_el, 'id', ''),
            label=_text(corresp_el.find('sup'))
        )
        for email_el in corresp_el.findall('email'):
            email = _text(email_el)
            corr.emails.append(email)
            # Extract author name from tail text: " (Author Name);" or " (Author Name)"
            tail = email_el.tail or ''
            name_match = re.search(r'\(([^)]+)\)', tail)
            if name_match:
                corr.authors.append(name_match.group(1))
        return corr

    def _parse_pub_dates(self, am) -> List[PubDate]:
        dates = []
        for pd in am.findall('pub-date'):
            dates.append(PubDate(
                pub_type=_attr(pd, 'pub-type', ''),
                day=_text(pd.find('day')),
                month=_text(pd.find('month')),
                year=_text(pd.find('year'))
            ))
        return dates

    def _parse_history(self, am) -> List[HistoryDate]:
        history = []
        hist_el = am.find('history')
        if hist_el is not None:
            for d in hist_el.findall('date'):
                history.append(HistoryDate(
                    date_type=_attr(d, 'date-type', ''),
                    day=_text(d.find('day')),
                    month=_text(d.find('month')),
                    year=_text(d.find('year'))
                ))
        return history

    def _parse_copyright(self, am) -> Optional[Copyright]:
        perm = am.find('permissions')
        if perm is None:
            return None
        c = Copyright(
            statement=_text(perm.find('copyright-statement')),
            year=_text(perm.find('copyright-year')),
        )
        license_el = perm.find('license')
        if license_el is not None:
            c.license_text = _text(license_el.find('license-p'))
            # Parse license-p as inline content to preserve links
            license_p = license_el.find('license-p')
            if license_p is not None:
                c.license_nodes = self._parse_inline_content(license_p)
            ext_link = license_el.find('.//{http://www.w3.org/1999/xlink}href')
            if ext_link is None:
                ext_link = license_el.find('.//ext-link')
                if ext_link is not None:
                    c.license_href = _attr(ext_link, '{http://www.w3.org/1999/xlink}href', '')
            else:
                c.license_href = _text(ext_link) if ext_link is not None else ""
        return c

    def _parse_abstract(self, am) -> Optional[Abstract]:
        abs_el = am.find('abstract')
        if abs_el is None:
            return None
        abstract = Abstract()
        for sec in abs_el.findall('sec'):
            section = AbstractSection(
                title=_text(sec.find('title')).rstrip(':').strip()
            )
            for p in sec.findall('p'):
                section.paragraphs.append(self._parse_inline_content(p))
            abstract.sections.append(section)
        # Also handle direct <p> in abstract (without <sec> wrapper)
        for p in abs_el.findall('p'):
            if not abstract.sections:
                abstract.sections.append(AbstractSection(title="", paragraphs=[]))
            abstract.sections[0].paragraphs.append(self._parse_inline_content(p))
        return abstract

    def _parse_keywords(self, am) -> List[KeywordGroup]:
        groups = []
        for kg in am.findall('kwd-group'):
            kwds = []
            for k in kg.findall('kwd'):
                kwds.append(_text(k))
            groups.append(KeywordGroup(
                group_type=_attr(kg, 'kwd-group-type', ''),
                keywords=kwds
            ))
        return groups

    # ── Body ──

    def _parse_body(self) -> Body:
        body_el = self.root.find('body')
        if body_el is None:
            return Body()

        body = Body()
        body.sections = self._parse_sections(body_el, level=0)
        return body

    def _parse_sections(self, parent_el, level: int) -> List[Section]:
        """Parse <sec> elements recursively."""
        sections = []
        for sec_el in parent_el.findall('sec'):
            section = Section(
                id=_attr(sec_el, 'id', ''),
                sec_type=_attr(sec_el, 'sec-type', ''),
                title=self._render_inline_to_text(sec_el.find('title')) if sec_el.find('title') is not None else "",
            )

            # Parse direct children: paragraphs, tables, figures, nested sections
            for child in sec_el:
                tag = etree.QName(child).localname if hasattr(child, 'tag') else ''
                if tag == 'p':
                    para = Paragraph(
                        id=_attr(child, 'id', ''),
                        content=self._parse_inline_content(child)
                    )
                    section.paragraphs.append(para)
                    section.children_in_order.append(('p', para))
                elif tag == 'table-wrap':
                    tw = self._parse_table_wrap(child)
                    section.tables.append(tw)
                    section.children_in_order.append(('table', tw))
                elif tag == 'fig':
                    fig = self._parse_figure(child)
                    section.figures.append(fig)
                    section.children_in_order.append(('fig', fig))
                elif tag == 'sec':
                    subsec = self._parse_single_section(child, level + 1)
                    section.sections.append(subsec)
                    section.children_in_order.append(('sec', subsec))

            sections.append(section)
        return sections

    def _parse_single_section(self, sec_el, level: int) -> Section:
        """Parse a single <sec> element (for nested sections)."""
        section = Section(
            id=_attr(sec_el, 'id', ''),
            sec_type=_attr(sec_el, 'sec-type', ''),
            title=self._render_inline_to_text(sec_el.find('title')) if sec_el.find('title') is not None else "",
        )
        for child in sec_el:
            tag = etree.QName(child).localname if hasattr(child, 'tag') else ''
            if tag == 'p':
                para = Paragraph(
                    id=_attr(child, 'id', ''),
                    content=self._parse_inline_content(child)
                )
                section.paragraphs.append(para)
                section.children_in_order.append(('p', para))
            elif tag == 'table-wrap':
                tw = self._parse_table_wrap(child)
                section.tables.append(tw)
                section.children_in_order.append(('table', tw))
            elif tag == 'fig':
                fig = self._parse_figure(child)
                section.figures.append(fig)
                section.children_in_order.append(('fig', fig))
            elif tag == 'sec':
                subsec = self._parse_single_section(child, level + 1)
                section.sections.append(subsec)
                section.children_in_order.append(('sec', subsec))
        return section

    # ── Inline Content Parsing ──

    def _parse_inline_content(self, el) -> List[InlineNode]:
        """Parse mixed content from an element into InlineNode list."""
        nodes = []
        if el is None:
            return nodes
        self._walk_inline(el, nodes)
        return nodes

    def _walk_inline(self, el, nodes: List[InlineNode]):
        """Recursively walk inline elements."""
        if el is None:
            return

        # Text before first child
        if el.text and el.text.strip():
            nodes.append(InlineText(text=el.text))

        for child in el:
            tag = etree.QName(child).localname if hasattr(child, 'tag') else ''

            if tag == 'italic':
                children = []
                self._walk_inline(child, children)
                nodes.append(InlineItalic(children=children))
            elif tag == 'bold':
                children = []
                self._walk_inline(child, children)
                nodes.append(InlineBold(children=children))
            elif tag == 'sup':
                children = []
                self._walk_inline(child, children)
                nodes.append(InlineSup(children=children))
            elif tag == 'sub':
                children = []
                self._walk_inline(child, children)
                nodes.append(InlineSub(children=children))
            elif tag == 'xref':
                rid = _attr(child, 'rid', '')
                ref_type = _attr(child, 'ref-type', '')
                nodes.append(InlineXref(
                    rid=rid,
                    ref_type=ref_type,
                    text=_text(child)
                ))
            elif tag in ('inline-formula', 'mml:math'):
                # Serialize the MathML to string
                if tag == 'inline-formula':
                    math_el = child.find('{http://www.w3.org/1998/Math/MathML}math')
                else:
                    math_el = child
                if math_el is not None:
                    mathml_str = etree.tostring(math_el, encoding='unicode')
                    nodes.append(InlineFormula(mathml=mathml_str))
            elif tag == 'break':
                nodes.append(InlineBreak())
            elif tag == 'ext-link':
                # External link — render as clickable hyperlink
                href = _attr(child, '{http://www.w3.org/1999/xlink}href', '')
                text = _text(child)
                if text == href or not text:
                    text = href
                nodes.append(InlineExtLink(href=href, text=text))
            elif tag in ('graphic', 'inline-graphic'):
                href = _attr(child, '{http://www.w3.org/1999/xlink}href', '')
                if href:
                    nodes.append(InlineGraphic(href=href))
            elif tag == 'mml:math':
                mathml_str = etree.tostring(child, encoding='unicode')
                nodes.append(InlineFormula(mathml=mathml_str))
            else:
                # For any other element, recurse into its children
                self._walk_inline(child, nodes)

            # Tail text after child
            if child.tail and child.tail.strip():
                nodes.append(InlineText(text=child.tail))

    def _render_inline_to_text(self, el) -> str:
        """Render inline content to plain text (for titles, captions, etc.)."""
        if el is None:
            return ""
        nodes = self._parse_inline_content(el)
        return self._flatten_nodes(nodes)

    def _flatten_nodes(self, nodes: List[InlineNode]) -> str:
        """Flatten inline nodes to plain text string."""
        result = []
        for node in nodes:
            if isinstance(node, InlineText):
                result.append(node.text)
            elif isinstance(node, InlineItalic):
                result.append(self._flatten_nodes(node.children))
            elif isinstance(node, InlineBold):
                result.append(self._flatten_nodes(node.children))
            elif isinstance(node, InlineSup):
                result.append(self._flatten_nodes(node.children))
            elif isinstance(node, InlineSub):
                result.append(self._flatten_nodes(node.children))
            elif isinstance(node, InlineXref):
                result.append(node.text)
            elif isinstance(node, InlineFormula):
                result.append("[Formula]")
            elif isinstance(node, InlineExtLink):
                result.append(node.text)
            elif isinstance(node, InlineGraphic):
                result.append("[Image]")
            elif isinstance(node, InlineBreak):
                result.append(" ")
        return ''.join(result)

    # ── Table Parsing ──

    def _parse_table_wrap(self, tw_el) -> TableWrap:
        tw = TableWrap(
            id=_attr(tw_el, 'id', ''),
            label=_text(tw_el.find('label'))
        )
        caption_el = tw_el.find('caption')
        if caption_el is not None:
            for p in caption_el.findall('p'):
                tw.caption.append(self._parse_inline_content(p))

        table_el = tw_el.find('table')
        if table_el is not None:
            tw.table = self._parse_table_content(table_el)
            tw.max_columns = self._count_table_columns(tw.table)

        # Footnotes
        twf = tw_el.find('table-wrap-foot')
        if twf is not None:
            for fn in twf.findall('fn'):
                tf = TableFootnote(id=_attr(fn, 'id', ''))
                for p in fn.findall('p'):
                    tf.paragraphs.append(self._parse_inline_content(p))
                tw.footnotes.append(tf)
        return tw

    def _count_table_columns(self, table_data) -> int:
        """Count the maximum number of effective columns across all rows.

        Accounts for colspan attributes. A table with many columns
        (>=6) is considered wide and should be rendered in landscape.
        """
        max_cols = 0
        all_rows = list(table_data.headers) + list(table_data.body)
        for row in all_rows:
            col_count = sum(max(1, cell.colspan) for cell in row.cells)
            if col_count > max_cols:
                max_cols = col_count
        return max_cols

    def _parse_table_content(self, table_el) -> TableData:
        td = TableData()
        thead = table_el.find('thead')
        if thead is not None:
            for tr_el in thead.findall('tr'):
                td.headers.append(self._parse_table_row(tr_el, 'th'))
        tbody = table_el.find('tbody')
        if tbody is not None:
            for tr_el in tbody.findall('tr'):
                td.body.append(self._parse_table_row(tr_el, 'td'))
        return td

    def _parse_table_row(self, tr_el, default_cell_type: str = 'td') -> TableRow:
        cells = []
        for cell_el in tr_el:
            tag = etree.QName(cell_el).localname if hasattr(cell_el, 'tag') else default_cell_type
            cell = TableCell(
                content=self._parse_inline_content(cell_el),
                colspan=int(_attr(cell_el, 'colspan', '1')),
                rowspan=int(_attr(cell_el, 'rowspan', '1')),
                style=_attr(cell_el, 'style', ''),
                align=_attr(cell_el, 'align', 'left'),
                cell_type=tag if tag in ('th', 'td') else default_cell_type,
            )
            cells.append(cell)
        return TableRow(cells=cells)

    # ── Figure Parsing ──

    def _parse_figure(self, fig_el) -> Figure:
        fig = Figure(
            id=_attr(fig_el, 'id', ''),
            label=_text(fig_el.find('label'))
        )
        caption_el = fig_el.find('caption')
        if caption_el is not None:
            for p in caption_el.findall('p'):
                fig.caption.append(self._parse_inline_content(p))

        graphic_el = fig_el.find('graphic')
        if graphic_el is not None:
            fig.graphic_href = _attr(graphic_el, '{http://www.w3.org/1999/xlink}href', '')
            fig.graphic_id = _attr(graphic_el, 'id', '')
        return fig

    # ── Back Matter ──

    def _parse_back(self) -> BackMatter:
        back_el = self.root.find('back')
        if back_el is None:
            return BackMatter()

        bm = BackMatter()

        for child in back_el:
            tag = etree.QName(child).localname if hasattr(child, 'tag') else ''

            if tag == 'sec':
                bm.sections.append(self._parse_single_section(child, 0))
            elif tag == 'ack':
                # Acknowledgments
                for p in child.findall('p'):
                    bm.acknowledgments.append(Paragraph(
                        content=self._parse_inline_content(p)
                    ))
            elif tag == 'ref-list':
                bm.references = self._parse_references(child)
            elif tag == 'fn-group':
                for fn in child.findall('fn'):
                    fg = FootnoteGroup()
                    for p in fn.findall('p'):
                        fg.paragraphs.append(self._parse_inline_content(p))
                    bm.footnotes.append(fg)
            # Handle supplementary material within sections
            elif tag == 'sec':
                sec = self._parse_single_section(child, 0)
                if sec.sec_type == 'supplementary-material':
                    sm_el = child.find('supplementary-material')
                    if sm_el is not None:
                        bm.supplementary_materials.append(SupplementaryMaterial(
                            id=_attr(sm_el, 'id', ''),
                            href=_attr(sm_el, '{http://www.w3.org/1999/xlink}href', ''),
                        ))
                bm.sections.append(sec)

        return bm

    def _parse_references(self, ref_list_el) -> List[Reference]:
        refs = []
        for ref_el in ref_list_el.findall('ref'):
            ref = Reference(
                id=_attr(ref_el, 'id', ''),
                label=_text(ref_el.find('label'))
            )
            citation_el = ref_el.find('element-citation')
            if citation_el is None:
                citation_el = ref_el.find('mixed-citation')
            if citation_el is not None:
                ref.citation = self._parse_citation(citation_el)
            refs.append(ref)
        return refs

    def _parse_citation(self, cit_el) -> ReferenceCitation:
        # Check if this is mixed-citation with raw text (no structured children)
        tag = etree.QName(cit_el).localname if hasattr(cit_el, 'tag') else ''
        if tag == 'mixed-citation':
            # mixed-citation may have raw text or structured children
            has_children = any(
                etree.QName(c).localname not in ('', None)
                for c in cit_el if hasattr(c, 'tag')
            )
            if not has_children and cit_el.text and cit_el.text.strip():
                # Pure text citation — store as raw
                cit = ReferenceCitation(
                    publication_type='journal',
                    comment=cit_el.text.strip(),
                )
                return cit

        cit = ReferenceCitation(
            publication_type=_attr(cit_el, 'publication-type', 'journal'),
            article_title=_text(cit_el.find('article-title')),
            source=_text(cit_el.find('source')),
            year=_text(cit_el.find('year')),
            volume=_text(cit_el.find('volume')),
            first_page=_text(cit_el.find('fpage')),
            last_page=_text(cit_el.find('lpage')),
            edition=_text(cit_el.find('edition')),
            publisher_name=_text(cit_el.find('publisher-name')),
            publisher_loc=_text(cit_el.find('publisher-loc')),
            comment=_text(cit_el.find('comment')),
            date_in_citation=_text(cit_el.find('date-in-citation')),
        )

        # Parse authors
        pg = cit_el.find('person-group')
        if pg is not None:
            for name_el in pg.findall('name'):
                sn = _text(name_el.find('surname'))
                gn = _text(name_el.find('given-names'))
                cit.authors.append(f"{sn} {gn}" if sn else gn)
            # Check for etal
            if pg.find('etal') is not None:
                cit.authors.append("et al.")

        # DOI
        ext_link = cit_el.find('ext-link')
        if ext_link is not None:
            cit.doi_href = _attr(ext_link, '{http://www.w3.org/1999/xlink}href', '')
            if 'doi.org' in cit.doi_href:
                cit.doi = cit.doi_href.replace('https://doi.org/', '').replace('http://doi.org/', '')

        # For web references, get the href
        if cit.publication_type == 'web' and not cit.doi_href:
            cit.ext_link_href = _attr(ext_link, '{http://www.w3.org/1999/xlink}href', '') if ext_link is not None else ''

        return cit

    def _parse_supplementary_materials(self, el) -> List[SupplementaryMaterial]:
        sm_list = []
        for sm in el.findall('.//supplementary-material'):
            sm_list.append(SupplementaryMaterial(
                id=_attr(sm, 'id', ''),
                href=_attr(sm, '{http://www.w3.org/1999/xlink}href', ''),
            ))
        return sm_list
