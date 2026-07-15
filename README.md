# JATS2PDF — JATS XML to PDF Automated Converter

**学术期刊结构化技术创新大赛 — 选题二：JATS XML → PDF 自动化映射与生成**

Convert JATS (Journal Article Tag Suite) XML files into publication-ready PDF documents
with automatic two-column layout, figure embedding, table rendering, MathML formula processing,
landscape table pages, and reference formatting.

## Features

- **Two-Column Layout**: Body text rendered in academic two-column format with column-span support for wide elements
- **Landscape Tables**: Wide tables (≥6 columns) automatically rendered on landscape (rotated) A4 pages
- **Full JATS 1.3 Support**: Parses JATS Publishing DTD v1.3 XML documents
- **Figure Embedding**: Automatic resolution and base64 embedding of figure images (JPG/PNG)
- **Table Rendering**: colspan/rowspan support, cell styling, three-line academic table style, table footnotes
- **MathML Processing**: Converts MathML formulas to Unicode/HTML for inline rendering
- **Reference Formatting**: Vancouver-style numbered references with DOI links and clickable URLs
- **Structured Abstract**: Renders abstract with bold section headings
- **Author Links**: ORCID links on author names, clickable email correspondence
- **Cross-References**: Blue clickable cross-references for bibliography, tables, and figures
- **Multi-Backend**: WeasyPrint (best quality, requires GTK3), Playwright/Chromium (full CSS support, auto-detected), xhtml2pdf (pure Python fallback)
- **Continuous Page Numbers**: Automatic page numbering across landscape/portrait mixed PDFs

## Quick Start

### Prerequisites

- Python 3.9+
- **Playwright** (auto-used when WeasyPrint unavailable): `playwright install chromium`
- For WeasyPrint backend (optional, best CSS Paged Media support):
  - Windows: Install [GTK3 Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
  - Linux: `sudo apt install libpango-1.0-0 libgdk-pixbuf2.0-0`
  - macOS: `brew install pango gdk-pixbuf`

### Installation

```bash
cd jats2pdf
pip install -r requirements.txt

# Install Chromium for Playwright backend (required on Windows without GTK3)
playwright install chromium
```

### Usage

```bash
# Basic usage
python run.py article.xml

# Specify output path
python run.py article.xml -o output.pdf

# Provide figure directory
python run.py article.xml -f ./figures/

# Generate HTML only (no PDF)
python run.py article.xml --html-only

# Verbose output
python run.py article.xml -v
```

### Extracting Figures

Figures in JATS are typically provided in a `figure.zip` file alongside the XML.
Extract them before running:

```bash
mkdir figures_extracted
unzip figure.zip -d figures_extracted/
python run.py article.xml -f figures_extracted/
```

## Project Structure

```
jats2pdf/
├── jats2pdf/                  # Main package
│   ├── __init__.py
│   ├── parser.py              # JATS XML parser (lxml, ~650 lines)
│   ├── models.py              # Data models (dataclasses)
│   ├── renderer.py            # Multi-backend PDF renderer
│   ├── math_handler.py        # MathML → HTML converter
│   ├── figure_resolver.py     # Image resolution & data URI embedding
│   ├── utils.py               # Utility functions
│   ├── cli.py                 # CLI entry point (Click)
│   └── templates/
│       ├── article.html       # Main Jinja2 template
│       ├── css/journal.css    # CSS Paged Media + two-column layout
│       └── components/        # Template components
├── tests/                     # Test suite
├── output/                    # Generated PDF/HTML output
├── run.py                     # Quick-start entry point
├── requirements.txt
├── setup.py
└── README.md
```

## PDF Backends

The converter auto-selects the best available backend:

| Priority | Backend | CSS Support | Requirements |
|----------|---------|-------------|--------------|
| 1 | WeasyPrint | Full (named pages, running headers) | GTK3 runtime |
| 2 | Playwright/Chromium | Excellent (columns, modern CSS) | `playwright install chromium` |
| 3 | xhtml2pdf | Basic (no columns, limited @page) | Pure Python |

## Supported JATS Elements

- **Front**: Journal meta, article IDs, contributors (authors/editors with ORCID), affiliations, correspondence, abstract (structured), keywords, dates, copyright
- **Body**: Multi-level sections, paragraphs with inline formatting (bold, italic, superscript, subscript, cross-references, external links, MathML formulas), tables, figures
- **Back**: Conclusions, data availability, author contributions, ethics, funding, conflicts of interest, acknowledgments, supplementary materials, references

## License

This project is developed for the IMR Academic Journal Structured Technology Innovation Competition.
