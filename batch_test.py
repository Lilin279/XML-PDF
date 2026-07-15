#!/usr/bin/env python
"""Batch test 5 main JATS XML samples."""
import os, sys, time, re, glob, zipfile

base = r'D:\JATSXML_PDF\样例-最新版\样例-最新版'
xml_files = []

for f in sorted(glob.glob(os.path.join(base, '样例*', '第二组', '初始文件.xml'))):
    xml_files.append(f)

print(f'Testing {len(xml_files)} samples...\n')
results = []

sys.path.insert(0, '.')
from jats2pdf.parser import JATSParser
from jats2pdf.renderer import PDFRenderer

for xml_path in xml_files:
    xml_dir = os.path.dirname(xml_path)
    name = os.path.basename(os.path.dirname(xml_dir))
    case = os.path.basename(os.path.dirname(os.path.dirname(xml_dir)))
    label = f'{case}/{name}'

    # Auto-extract figures zip
    for zip_name in ['figures.zip', 'figure.zip']:
        zp = os.path.join(xml_dir, zip_name)
        if os.path.exists(zp):
            ed = os.path.join(xml_dir, '_auto_extracted')
            if not os.path.exists(ed):
                os.makedirs(ed)
                with zipfile.ZipFile(zp, 'r') as zf:
                    zf.extractall(ed)
            break

    out_dir = r'D:\JATSXML_PDF\jats2pdf\output\test'
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{case}_{name}.pdf')

    try:
        t0 = time.time()
        parser = JATSParser(xml_path)
        article = parser.parse()
        renderer = PDFRenderer(article=article)

        ed = os.path.join(xml_dir, '_auto_extracted')
        if os.path.isdir(ed):
            renderer.figure_resolver.add_search_dir(ed)

        renderer.render_pdf(out)
        elapsed = time.time() - t0

        with open(out, 'rb') as f:
            data = f.read()
        pages = max(int(c) for c in re.findall(rb'/Count\s+(\d+)', data)) if data else 0
        size_kb = len(data) / 1024

        title = article.front.article_title[:50] if article.front.article_title else '?'
        print(f'  OK  {label:20s}  {pages:2d}p  {size_kb:6.0f}KB  {elapsed:4.1f}s  {title[:40]}')
        results.append((label, pages, size_kb, elapsed, 'OK'))
    except Exception as e:
        print(f'  FAIL  {label:20s}  {str(e)[:100]}')
        results.append((label, 0, 0, 0, str(e)[:100]))

print(f'\nSummary:')
total_pages = sum(r[1] for r in results)
total_size = sum(r[2] for r in results)
for r in results:
    status = 'OK' if r[4] == 'OK' else 'FAIL'
    print(f'  {status:4s}  {r[0]:20s}  {r[1]:2d}p  {r[2]:6.0f}KB  {r[3]:4.1f}s')
print(f'Total: {total_pages} pages, {total_size:.0f} KB')
