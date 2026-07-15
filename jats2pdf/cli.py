"""Command-line interface for JATS2PDF converter."""

import sys
import os
from pathlib import Path

import click

from .parser import JATSParser
from .renderer import PDFRenderer
from .figure_resolver import auto_detect_figure_dir


@click.command()
@click.argument('xml_file', type=click.Path(exists=True))
@click.option('-o', '--output', default=None,
              help='Output PDF file path (default: input_name.pdf)')
@click.option('-f', '--figures-dir', default=None,
              help='Directory containing extracted figure files')
@click.option('--html-only', is_flag=True, default=False,
              help='Output HTML only (no PDF generation)')
@click.option('--template-dir', default=None,
              help='Custom Jinja2 template directory')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Enable verbose output')
def main(xml_file, output, figures_dir, html_only, template_dir, verbose):
    """Convert JATS XML academic articles to publication-ready PDF.

    XML_FILE: Path to the JATS XML input file.

    Examples:

        jats2pdf article.xml

        jats2pdf article.xml -o output.pdf -f ./figures/

        jats2pdf article.xml --html-only  # Generate HTML only
    """
    xml_path = Path(xml_file).resolve()

    if verbose:
        click.echo(f"JATS2PDF - Academic Journal XML to PDF Converter")
        click.echo(f"Input: {xml_path}")

    # Parse XML
    if verbose:
        click.echo("Parsing JATS XML...")
    try:
        parser = JATSParser(str(xml_path))
        article = parser.parse()
    except Exception as e:
        click.echo(f"Error parsing XML: {e}", err=True)
        sys.exit(1)

    if verbose:
        title = article.front.article_title[:80] if article.front.article_title else "(no title)"
        click.echo(f"  Title: {title}...")
        click.echo(f"  Authors: {len(article.front.authors)}")
        click.echo(f"  Sections: {len(article.body.sections)}")
        click.echo(f"  References: {len(article.back.references)}")

    # Resolve figures directory
    figure_search_dirs = []
    if figures_dir:
        fig_path = Path(figures_dir).resolve()
        if fig_path.is_dir():
            figure_search_dirs.append(str(fig_path))
        else:
            click.echo(f"Warning: Figures directory not found: {figures_dir}", err=True)
    else:
        # Auto-detect
        auto_fig = auto_detect_figure_dir(xml_path)
        if auto_fig:
            figure_search_dirs.append(str(auto_fig))
            if verbose:
                click.echo(f"  Auto-detected figures: {auto_fig}")

    # Determine output path
    if output is None:
        if html_only:
            output = str(xml_path.with_suffix('.html'))
        else:
            output = str(xml_path.with_suffix('.pdf'))
    output_path = str(Path(output).resolve())

    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Render
    if verbose:
        click.echo("Rendering...")

    try:
        renderer = PDFRenderer(
            article=article,
            template_dir=template_dir,
            figures_dir=figures_dir,
            figure_search_dirs=figure_search_dirs,
        )

        if html_only:
            html = renderer.render_html()
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            click.echo(f"HTML written to: {html_path}")
        else:
            result = renderer.render_pdf(output_path)
            click.echo(f"PDF written to: {result}")
            # Also keep the intermediate HTML alongside PDF
            html_path = output_path.replace('.pdf', '.html')
            click.echo(f"Intermediate HTML: {html_path}")

    except Exception as e:
        click.echo(f"Error rendering: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
