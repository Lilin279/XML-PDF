#!/usr/bin/env python
"""Quick-start entry point for JATS2PDF converter.

Usage:
    python run.py <xml_file> [-o output.pdf] [-f figures_dir]
"""

from jats2pdf.cli import main

if __name__ == '__main__':
    main()
