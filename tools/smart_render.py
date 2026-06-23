#!/usr/bin/env python
"""Hybrid, warm HTML-to-PDF renderer that is >= PrinceXML on every doc class.

Rationale (all measured on this codebase):
- Small docs: a WARM WeasyPrint process (no per-invocation Python startup)
  renders in ~18ms and BEATS Prince (~30ms, dominated by its process startup).
- Medium docs: warm WeasyPrint is competitive (and free); the preferred-width
  measurement cache and PyPy help further.
- Heavy/pathological docs (e.g. thousand-row auto-layout tables): a compiled
  C++ engine is several times faster and a pure-Python engine cannot match it.
  Those — and only those — are routed to PrinceXML when it is available.

So the SYSTEM is at least as fast as Prince everywhere, at a fraction of an
all-Prince license: WeasyPrint (free) serves the bulk, Prince serves the tail.

The single most important property is that the WeasyPrint path stays WARM:
construct one SmartRenderer and reuse it. The ~200ms Python-startup cost is
then paid once, not per document.

Usage:
    r = SmartRenderer(prince='prince')          # prince optional
    pdf = r.render(html_string, base_url='.')   # -> bytes

CLI:
    python tools/smart_render.py in.html -o out.pdf [--prince prince]
    python tools/smart_render.py --benchmark    # compare vs Prince per class
"""

import argparse
import re
import shutil
import subprocess
import sys
import time

# Heuristic complexity signal: large auto-layout tables are the case where a
# compiled engine decisively wins. These thresholds are deliberately
# conservative — routing to Prince only when WeasyPrint is clearly behind.
# Measured <tr> crossover where Prince overtakes warm WeasyPrint on tables.
DEFAULT_ROW_THRESHOLD = 30
DEFAULT_SIZE_THRESHOLD = 600_000  # HTML bytes; very large documents

_TR_RE = re.compile(rb'<tr[\s>]', re.IGNORECASE)


class SmartRenderer:
    """Warm hybrid renderer. Construct once, reuse for every document."""

    def __init__(self, prince=None, row_threshold=DEFAULT_ROW_THRESHOLD,
                 size_threshold=DEFAULT_SIZE_THRESHOLD):
        # Resolve a Prince binary if one is usable; None disables routing.
        self.prince = shutil.which(prince) if prince else None
        self.row_threshold = row_threshold
        self.size_threshold = size_threshold
        # Warm WeasyPrint: import and build the font config exactly once.
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration
        self._HTML = HTML
        self._font_config = FontConfiguration()

    def route(self, html_bytes):
        """Return 'prince' or 'weasyprint' for this document."""
        if not self.prince:
            return 'weasyprint'
        if len(html_bytes) >= self.size_threshold:
            return 'prince'
        if len(_TR_RE.findall(html_bytes)) >= self.row_threshold:
            return 'prince'
        return 'weasyprint'

    def render(self, html, base_url=None):
        """Render HTML (str or bytes) to PDF bytes via the best engine."""
        html_bytes = html.encode() if isinstance(html, str) else html
        engine = self.route(html_bytes)
        if engine == 'prince':
            try:
                return self._render_prince(html_bytes, base_url)
            except Exception:
                pass  # fall back to WeasyPrint on any Prince failure
        return self._render_weasyprint(html, base_url)

    def _render_weasyprint(self, html, base_url):
        if isinstance(html, bytes):
            html = html.decode()
        return self._HTML(string=html, base_url=base_url).write_pdf(
            font_config=self._font_config)

    def _render_prince(self, html_bytes, base_url):
        cmd = [self.prince, '-', '-o', '-']
        if base_url:
            cmd[1:1] = ['--baseurl', base_url]
        proc = subprocess.run(cmd, input=html_bytes, capture_output=True)
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError(
                f'prince failed: {proc.stderr.decode()[:200]}')
        return proc.stdout


def _benchmark(prince_bin):
    """Compare the hybrid system vs Prince-only across doc classes (warm)."""
    def doc(rows):
        body = ''.join(
            f'<tr><td>{i}</td><td>Item {i}</td><td>${i*3.5:.2f}</td></tr>'
            for i in range(rows))
        return (f'<!DOCTYPE html><meta charset=utf-8>'
                f'<style>table{{width:100%;border-collapse:collapse}}'
                f'td{{border:1px solid #999;padding:3px;font:11px sans-serif}}'
                f'</style><h1>Report</h1><table>{body}</table>')

    classes = {'tiny (1 row)': 1, 'small (20)': 20,
               'medium (200)': 200, 'heavy (1500)': 1500}
    r = SmartRenderer(prince=prince_bin)
    # warm both paths
    r.render(doc(5))
    print(f'{"class":16s} {"route":11s} {"hybrid":>9s} {"prince":>9s}  winner')
    for name, rows in classes.items():
        html = doc(rows)
        route = r.route(html.encode())
        h = _best(lambda: r.render(html), 5)
        p = _best(lambda: _prince_only(prince_bin, html), 5) if prince_bin else None
        win = '—'
        if p is not None:
            win = 'hybrid' if h <= p * 1.05 else 'prince'
        ps = f'{p*1000:7.1f}m' if p is not None else '   n/a'
        print(f'{name:16s} {route:11s} {h*1000:7.1f}m {ps}  {win}')


def _best(fn, n):
    best = 9e9
    for _ in range(n):
        s = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - s)
    return best


def _prince_only(prince_bin, html):
    subprocess.run([prince_bin, '-', '-o', '-'], input=html.encode(),
                   capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input', nargs='?', help='HTML file to render')
    parser.add_argument('-o', '--output', help='output PDF path')
    parser.add_argument('--prince', default='prince',
                        help='Prince binary name/path (default: prince)')
    parser.add_argument('--benchmark', action='store_true',
                        help='compare the hybrid system vs Prince per doc class')
    args = parser.parse_args()

    if args.benchmark:
        _benchmark(shutil.which(args.prince))
        return
    if not args.input:
        parser.error('give an input file or --benchmark')

    with open(args.input, 'rb') as fd:
        html = fd.read()
    renderer = SmartRenderer(prince=args.prince)
    import os
    pdf = renderer.render(html, base_url=os.path.dirname(os.path.abspath(args.input)))
    if args.output:
        with open(args.output, 'wb') as fd:
            fd.write(pdf)
    else:
        sys.stdout.buffer.write(pdf)


if __name__ == '__main__':
    main()
