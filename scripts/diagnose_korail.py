"""Read-only Korail page diagnostics. Prints no cookies or personal data."""
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from html.parser import HTMLParser
import re

URL = 'https://www.korail.com/tour/themeTravel/areaThemes/all'

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.forms = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'script' and d.get('src'):
            self.scripts.append(urljoin(URL, d['src']))
        if tag == 'form':
            self.forms.append((d.get('action'), d.get('method')))

req = Request(URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; RailTravelDiagnostics/1.0)', 'Accept': 'text/html'})
try:
    with urlopen(req, timeout=20) as response:
        raw = response.read(2_000_000)
        html = raw.decode('utf-8', errors='replace')
        print('HTTP_STATUS:', response.status)
        print('FINAL_URL:', response.url)
        print('HTML_LENGTH:', len(html))
        title = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
        print('TITLE:', re.sub(r'\s+', ' ', title.group(1)).strip()[:120] if title else '(none)')
        print('PRICE_MARKERS:', html.count('원'))
        print('GOODS_LINK_COUNT:', len(set(re.findall(r'/tour/goods/[A-Za-z0-9]+', html))))
        p = Inspector()
        p.feed(html)
        print('SCRIPT_COUNT:', len(p.scripts))
        print('SCRIPT_URLS (first 25):')
        for s in p.scripts[:25]:
            print(' ', s)
        print('FORM_ACTIONS:', p.forms[:10])
        print('HTML_HINTS:', {x: html.lower().count(x.lower()) for x in ['api/', 'axios', 'fetch(', 'productPopularity', 'areaThemes', 'goodsList', '__NEXT_DATA__']})
        print('DIAGNOSTIC_COMPLETE')
except Exception as e:
    print('DIAGNOSTIC_ERROR:', type(e).__name__, str(e)[:300])
    raise
