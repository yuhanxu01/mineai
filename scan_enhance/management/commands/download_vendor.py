"""
Management command: download all CDN assets used in index.html into static/vendor/
so they can be served as a fallback if CDN is unreachable.

Usage:
    python manage.py download_vendor
    python manage.py download_vendor --timeout 30
"""
import sys
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

# All CDN assets referenced in index.html
VENDOR_ASSETS = [
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js',
        'filename': 'react.production.min.js',
    },
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js',
        'filename': 'react-dom.production.min.js',
    },
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.9/babel.min.js',
        'filename': 'babel.min.js',
    },
    {
        'url': 'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
        'filename': 'marked.min.js',
    },
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js',
        'filename': 'cytoscape.min.js',
    },
    {
        'url': 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js',
        'filename': 'mathjax-tex-chtml.js',
    },
]

# Google Fonts CSS (the @font-face declarations) — downloaded as a CSS file
FONT_ASSETS = [
    {
        'url': (
            'https://fonts.googleapis.com/css2?'
            'family=Noto+Serif+SC:wght@400;600;700'
            '&family=Noto+Sans+SC:wght@300;400;500;600'
            '&family=JetBrains+Mono:wght@400;500&display=swap'
        ),
        'filename': 'google-fonts.css',
        # User-Agent needed so Google Fonts returns woff2 for modern browsers
        'ua': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    },
]


class Command(BaseCommand):
    help = 'Download CDN assets to static/vendor/ for offline/fallback serving'

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=20,
                            help='HTTP request timeout in seconds (default: 20)')
        parser.add_argument('--force', action='store_true',
                            help='Re-download even if file already exists')

    def handle(self, *args, **options):
        timeout = options['timeout']
        force = options['force']

        # Determine vendor directory
        static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
        if static_dirs:
            vendor_dir = Path(static_dirs[0]) / 'vendor'
        else:
            vendor_dir = Path(settings.BASE_DIR) / 'static' / 'vendor'

        vendor_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f'Vendor directory: {vendor_dir}\n')

        all_assets = VENDOR_ASSETS + FONT_ASSETS
        ok = 0
        skip = 0
        fail = 0

        for asset in all_assets:
            dest = vendor_dir / asset['filename']
            if dest.exists() and not force:
                self.stdout.write(self.style.WARNING(f'  SKIP (exists) {asset["filename"]}'))
                skip += 1
                continue

            self.stdout.write(f'  GET  {asset["url"][:80]}...')
            try:
                req = urllib.request.Request(asset['url'])
                req.add_header('User-Agent', asset.get(
                    'ua',
                    'Mozilla/5.0 MineAI-VendorDownloader/1.0'
                ))
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                dest.write_bytes(data)
                self.stdout.write(self.style.SUCCESS(
                    f'       -> {asset["filename"]} ({len(data)//1024} KB)'
                ))
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'       FAIL: {e}'))
                fail += 1

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Done: {ok} downloaded, {skip} skipped, {fail} failed')
        )
        if fail:
            self.stdout.write(self.style.WARNING(
                'Failed assets will still be served from CDN; '
                'only successfully downloaded files become fallbacks.'
            ))
