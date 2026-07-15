"""PDF Renderer — converts parsed Article to PDF via Jinja2 + multiple backends.

Supported backends:
- weasyprint: Best CSS Paged Media support (requires GTK3 on Windows)
- xhtml2pdf: Pure Python fallback (works everywhere, limited CSS)
"""

import os
import sys
import tempfile
import logging
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Article, InlineFormula
from .math_handler import mathml_to_html
from .figure_resolver import FigureResolver

logger = logging.getLogger(__name__)


class PDFRenderer:
    """Render a parsed Article object to PDF using Jinja2 and available backends."""

    BACKEND_WEASYPRINT = 'weasyprint'
    BACKEND_XHTML2PDF = 'xhtml2pdf'
    BACKEND_AUTO = 'auto'

    def __init__(self, article: Article,
                 template_dir: Optional[str] = None,
                 figures_dir: Optional[str] = None,
                 figure_search_dirs: Optional[list] = None,
                 backend: str = BACKEND_AUTO):
        """Initialize the PDF renderer.

        Args:
            article: Parsed Article object.
            template_dir: Path to Jinja2 templates directory.
            figures_dir: Path to directory with extracted figures.
            figure_search_dirs: Additional directories to search for figures.
            backend: PDF backend ('weasyprint', 'xhtml2pdf', or 'auto').
        """
        self.article = article
        self.backend = backend

        # Template setup
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Figure resolver setup
        self.figure_resolver = FigureResolver()
        if figures_dir:
            self.figure_resolver.add_search_dir(figures_dir)
        if figure_search_dirs:
            for d in figure_search_dirs:
                self.figure_resolver.add_search_dir(d)
        # Auto-detect figures near the XML file
        if article.xml_path:
            xml_dir = Path(article.xml_path).parent
            self.figure_resolver.add_search_dir(xml_dir)
            for name in ['figures', 'figure', 'figs']:
                candidate = xml_dir / name
                if candidate.is_dir():
                    self.figure_resolver.add_search_dir(candidate)

    def render_html(self) -> str:
        """Render the article to complete HTML string.

        Returns:
            Complete HTML document as string.
        """
        # Pre-process: convert all inline formulas from MathML to HTML
        self._preprocess_formulas()

        # Resolve figure URIs
        figure_uris = self._resolve_figures()

        # Render template
        template = self.env.get_template('article.html')
        html = template.render(
            article=self.article,
            figure_uris=figure_uris,
        )

        # Post-process: fix common issues
        html = self._post_process_html(html)

        return html

    def _post_process_html(self, html: str) -> str:
        """Apply post-processing fixes to the rendered HTML."""
        import re

        # Fix "Discussions" -> "Discussion" (academic convention)
        html = html.replace('>4. Discussions<', '>4. Discussion<')

        # Fix bracket spacing: [ 1 ] -> [1], [ 16 , 17 ] -> [16,17]
        # Match brackets containing numbers/commas with internal whitespace
        html = re.sub(
            r'\[\s+(\d+(?:\s*,\s*\d+)*)\s+\]',
            lambda m: '[' + re.sub(r'\s*,\s*', ',', m.group(1).strip()) + ']',
            html
        )

        return html

    def render_pdf(self, output_path: str) -> str:
        """Render the article to PDF file.

        Args:
            output_path: Path for the output PDF file.

        Returns:
            Path to the generated PDF file.
        """
        html = self.render_html()

        # Always write intermediate HTML for debugging
        html_path = output_path.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"Intermediate HTML written to: {html_path}")

        # Determine which backend to use
        backend = self._resolve_backend()

        if backend == self.BACKEND_WEASYPRINT:
            return self._render_with_weasyprint(html, output_path)
        elif backend == 'playwright':
            return self._render_with_playwright(html, output_path)
        else:
            return self._render_with_xhtml2pdf(html, output_path)

    def _resolve_backend(self) -> str:
        """Determine which PDF backend to use."""
        if self.backend == self.BACKEND_WEASYPRINT:
            return self.BACKEND_WEASYPRINT
        if self.backend == self.BACKEND_XHTML2PDF:
            return self.BACKEND_XHTML2PDF

        # Auto-detect: try WeasyPrint first, then Playwright, then xhtml2pdf
        try:
            import weasyprint
            logger.info("Using WeasyPrint backend")
            return self.BACKEND_WEASYPRINT
        except (ImportError, OSError) as e:
            logger.warning(f"WeasyPrint not available: {e}")

        # Try Playwright (Chromium-based, full CSS support including columns)
        try:
            from playwright.sync_api import sync_playwright
            logger.info("Using Playwright (Chromium) backend")
            return 'playwright'
        except ImportError:
            pass

        logger.info("Falling back to xhtml2pdf backend")
        return self.BACKEND_XHTML2PDF

    def _render_with_weasyprint(self, html: str, output_path: str) -> str:
        """Render HTML to PDF using WeasyPrint (best CSS Paged Media support)."""
        from weasyprint import HTML

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', encoding='utf-8', delete=False
        ) as tmp:
            tmp.write(html)
            tmp_path = tmp.name

        try:
            doc = HTML(filename=tmp_path)
            doc.write_pdf(output_path)
            logger.info(f"PDF (WeasyPrint) written to: {output_path}")
        finally:
            os.unlink(tmp_path)

        return output_path

    def _render_with_playwright(self, html: str, output_path: str) -> str:
        """Render HTML to PDF using Playwright (Chromium-based).

        Chromium supports CSS columns and modern layout.
        Landscape tables are rendered separately and merged via PyPDF2.
        """
        # Check if there are landscape tables to handle
        if 'class="landscape-table-wrap"' not in html:
            return self._playwright_render_single(html, output_path, 'A4')

        # Split HTML: render segments in portrait/landscape, then merge
        return self._render_with_landscape_tables(html, output_path)

    def _playwright_render_single(self, html: str, output_path: str,
                                   page_format: str = 'A4') -> str:
        """Render a single HTML to PDF using Playwright."""
        from playwright.sync_api import sync_playwright
        import os as _os

        browser_paths = [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ]

        executable_path = None
        for p in browser_paths:
            if _os.path.exists(p):
                executable_path = p
                break

        launch_args = {'headless': True}
        if executable_path:
            launch_args['executable_path'] = executable_path

        # Write HTML to temp file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', encoding='utf-8', delete=False
        ) as tmp:
            tmp.write(html)
            tmp_path = tmp.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                page = browser.new_page()

                page.goto(f'file:///{tmp_path.replace(chr(92), chr(47))}')
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)

                page.pdf(
                    path=output_path,
                    format=page_format,
                    print_background=True,
                    prefer_css_page_size=True,
                )

                browser.close()
        finally:
            os.unlink(tmp_path)

        logger.info(f"PDF (Playwright) written to: {output_path}")
        return output_path

    def _render_with_landscape_tables(self, html: str, output_path: str) -> str:
        """Render HTML with landscape table pages merged inline via PyPDF2.

        Splits the HTML at landscape table boundaries, renders each segment
        with the appropriate page orientation, merges in order, and stamps
        continuous page numbers on all pages.
        """
        from PyPDF2 import PdfReader, PdfWriter, Transformation
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        import io

        # Extract HTML wrapper
        body_start = html.find('<body>') + len('<body>')
        body_end = html.find('</body>')
        html_head = html[:body_start]
        html_foot = html[body_end:]
        body_content = html[body_start:body_end]

        # Remove built-in page counter from CSS (we stamp manually)
        css_clean = html_head
        css_clean = css_clean.replace(
            'content: counter(page);', 'content: "";'
        )

        # Split body at landscape table boundaries
        LANDMARK = '<div class="landscape-table-wrap">'
        segments = self._split_at_landscape_divs(body_content, LANDMARK)

        # Build ordered segments
        ordered_segments = []
        for seg in segments:
            if not seg.strip():
                continue
            is_landscape = 'class="landscape-table-wrap"' in seg
            ordered_segments.append((seg, is_landscape))

        # Render each segment
        temp_pdfs = []
        for i, (seg_content, is_landscape) in enumerate(ordered_segments):
            seg_path = output_path.replace('.pdf', f'_seg_{i}.pdf')

            if is_landscape:
                seg_html = css_clean + seg_content + html_foot
                seg_html = seg_html.replace(
                    'size: A4;', 'size: A4 landscape;'
                )
                self._playwright_render_single(seg_html, seg_path, 'A4')
            else:
                # Portrait segment
                seg_html = css_clean + seg_content + html_foot
                # Wrap body content in two-column div if needed
                if ('class="two-column-body"' not in seg_content
                        and 'class="single-column-front"' not in seg_content
                        and seg_content.strip()):
                    seg_html = (css_clean
                                + '<div class="two-column-body">'
                                + seg_content
                                + '</div>'
                                + html_foot)
                self._playwright_render_single(seg_html, seg_path, 'A4')

            temp_pdfs.append(seg_path)

        # Merge all segment PDFs in order
        merger = PdfWriter()
        for pdf_path in temp_pdfs:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                merger.add_page(page)

        # Stamp continuous page numbers on merged PDF
        total_pages = len(merger.pages)
        for page_num in range(total_pages):
            page = merger.pages[page_num]
            # Create a page-number stamp PDF
            packet = io.BytesIO()
            # Use A4 portrait or landscape based on page dimensions
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            can = canvas.Canvas(packet, pagesize=(w, h))
            can.setFont("Times-Roman", 10)
            # Center bottom
            page_text = str(page_num + 1)
            can.drawCentredString(w / 2, 30, page_text)
            can.save()
            packet.seek(0)
            stamp_reader = PdfReader(packet)
            if stamp_reader.pages:
                page.merge_page(stamp_reader.pages[0])

        with open(output_path, 'wb') as f:
            merger.write(f)

        # Cleanup
        for p in temp_pdfs:
            try:
                os.unlink(p)
            except OSError:
                pass

        logger.info(f"PDF (Playwright + merge, {total_pages} pages) written to: {output_path}")
        return output_path

    def _render_with_xhtml2pdf(self, html: str, output_path: str) -> str:
        """Render HTML to PDF using xhtml2pdf (pure Python fallback)."""
        from xhtml2pdf import pisa

        # xhtml2pdf doesn't support @page with running headers/footers
        # Remove all @page blocks and inject a simple one
        html_fixed = self._fix_css_for_xhtml2pdf(html)

        with open(output_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(
                html_fixed, dest=pdf_file,
                encoding='utf-8',
            )

        if pisa_status.err:
            logger.warning(f"xhtml2pdf warnings: {pisa_status.err}")

        logger.info(f"PDF (xhtml2pdf) written to: {output_path}")
        return output_path

    def _fix_css_for_xhtml2pdf(self, html: str) -> str:
        """Replace CSS with xhtml2pdf-compatible version.

        xhtml2pdf only supports basic @page { size; margin; } without
        @top-* or @bottom-* nested rules.
        """
        import re

        style_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
        if not style_match:
            return html

        css = style_match.group(1)

        # Remove all @page rules with proper brace matching
        css = self._remove_at_page_blocks(css)

        # Remove string-set properties (not supported)
        css = re.sub(r'string-set:\s*[^;]+;\s*', '', css)

        # Clean up excessive blank lines
        css = re.sub(r'\n\s*\n\s*\n+', '\n\n', css)

        # Add simple xhtml2pdf-compatible @page rule
        simple_page = '@page { size: A4; margin: 2.5cm 2cm 3cm 2cm; }\n\n'
        css = simple_page + css

        # Replace style tag content
        html = html[:style_match.start(1)] + css + html[style_match.end(1):]

        # Add page number footer
        html = html.replace('</body>',
            '<div style="text-align:center; font-size:10pt; margin-top:12pt;">'
            '<pdf:pagenumber> / <pdf:pagecount></div>'
            '</body>')

        # Fix bracket spacing: [ 1 ] -> [1], [ 16 , 17 ] -> [16,17]
        html = re.sub(
            r'\[\s+(\d+(?:\s*,\s*\d+)*)\s+\]',
            lambda m: '[' + re.sub(r'\s*,\s*', ',', m.group(1).strip()) + ']',
            html
        )

        return html

    @staticmethod
    def _split_at_landscape_divs(body_html: str, landmark: str) -> list:
        """Split HTML body at landscape table wrapper divs.

        Uses div-counting to correctly match nested <div> / </div> pairs
        so the full table content (with nested divs) is captured.

        Returns a list of HTML segments, alternating between
        portrait content and landscape table blocks.
        """
        import re
        segments = []
        pos = 0

        while True:
            idx = body_html.find(landmark, pos)
            if idx == -1:
                # No more landscape blocks; add remaining content
                remaining = body_html[pos:]
                if remaining.strip():
                    segments.append(remaining)
                break

            # Add content before this landscape block
            before = body_html[pos:idx]
            if before.strip():
                segments.append(before)

            # Find matching </div> by counting nested divs
            depth = 1
            search_pos = idx + len(landmark)
            div_open = re.compile(r'<div\b', re.IGNORECASE)
            div_close = re.compile(r'</div>', re.IGNORECASE)

            while depth > 0 and search_pos < len(body_html):
                next_open = div_open.search(body_html, search_pos)
                next_close = div_close.search(body_html, search_pos)

                if next_close is None:
                    break

                if next_open and next_open.start() < next_close.start():
                    depth += 1
                    search_pos = next_open.end()
                else:
                    depth -= 1
                    if depth == 0:
                        search_pos = next_close.end()
                        break
                    search_pos = next_close.end()

            # Extract the full landscape block
            land_block = body_html[idx:search_pos]
            segments.append(land_block)
            pos = search_pos

        return segments

    @staticmethod
    def _remove_at_page_blocks(css: str) -> str:
        """Remove @page and @page :first blocks with proper brace matching.

        Handles nested braces from @top-left, @bottom-center, etc.
        """
        result = []
        i = 0
        while i < len(css):
            # Check for @page at current position
            if css[i:i+5] == '@page':
                # Find the opening brace
                brace_start = css.find('{', i)
                if brace_start == -1:
                    result.append(css[i:])
                    break
                # Find matching closing brace
                depth = 0
                j = brace_start
                while j < len(css):
                    if css[j] == '{':
                        depth += 1
                    elif css[j] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                # Skip the entire @page block
                i = j + 1
                continue
            result.append(css[i])
            i += 1

        return ''.join(result)

    def _preprocess_formulas(self):
        """Convert all MathML formulas in the article to HTML."""
        def convert_nodes(nodes):
            if not nodes:
                return
            for node in nodes:
                if isinstance(node, InlineFormula):
                    node.mathml = mathml_to_html(node.mathml, is_inline=True)
                elif hasattr(node, 'children') and node.children:
                    convert_nodes(node.children)

        # Walk all paragraphs in body
        for section in self.article.body.sections:
            self._walk_section_formulas(section)

        # Walk all paragraphs in back matter
        for section in self.article.back.sections:
            self._walk_section_formulas(section)

        # Walk abstract
        if self.article.front.abstract:
            for abs_sec in self.article.front.abstract.sections:
                for para in abs_sec.paragraphs:
                    convert_nodes(para)

        # Walk copyright license nodes
        if self.article.front.copyright and self.article.front.copyright.license_nodes:
            convert_nodes(self.article.front.copyright.license_nodes)

        # Walk acknowledgments
        for para in self.article.back.acknowledgments:
            convert_nodes(para.content)

    def _walk_section_formulas(self, section):
        """Recursively convert formulas in a section tree."""
        for para in section.paragraphs:
            if para.content:
                self._convert_nodes(para.content)
        for table in section.tables:
            # Captions
            for cap in table.caption:
                self._convert_nodes(cap)
            # Table cells
            if table.table:
                for row in table.table.headers + table.table.body:
                    for cell in row.cells:
                        self._convert_nodes(cell.content)
            # Footnotes
            for fn in table.footnotes:
                for p in fn.paragraphs:
                    self._convert_nodes(p)
        for fig in section.figures:
            for cap in fig.caption:
                self._convert_nodes(cap)
        for subsec in section.sections:
            self._walk_section_formulas(subsec)

    def _convert_nodes(self, nodes):
        """Recursively convert formula nodes in a list."""
        if not nodes:
            return
        for node in nodes:
            if isinstance(node, InlineFormula):
                node.mathml = mathml_to_html(node.mathml, is_inline=True)
            elif hasattr(node, 'children') and node.children:
                self._convert_nodes(node.children)

    def _resolve_figures(self) -> dict:
        """Resolve all figure hrefs to data URIs.

        Returns:
            Dict mapping graphic_href to data: URI string.
        """
        uris = {}
        figures = self._collect_all_figures()
        for fig in figures:
            if fig.graphic_href and fig.graphic_href not in uris:
                uri = self.figure_resolver.resolve_to_data_uri(fig.graphic_href)
                if uri:
                    uris[fig.graphic_href] = uri
        return uris

    def _collect_all_figures(self) -> list:
        """Collect all figures from body and back matter."""
        figures = []

        def walk_sections(sections):
            for sec in sections:
                figures.extend(sec.figures)
                walk_sections(sec.sections)

        walk_sections(self.article.body.sections)
        walk_sections(self.article.back.sections)
        return figures
