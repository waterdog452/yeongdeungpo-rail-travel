#!/usr/bin/env python3
"""Conservative public-page importer. No login, bypass, or private endpoints.

Only publish when actual HTTP HTML contains a recognizable set of product cards.
Run only where the site's published access rules permit automated fetching.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'products.json'
URL = 'https://www.korail.com/tour'
REGIONS = ('전라권','강원권','충청권','경상권','수도권','제주권')


def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    for el in soup(['script','style','noscript']): el.decompose()
    candidates = []
    # Restrict extraction to cards that visibly contain an individual product and price.
    for el in soup.select('li, article, [class*=product], [class*=goods], [class*=item]'):
        raw = el.get_text(' ', strip=True)
        if not 8 <= len(raw) <= 650: continue
        if not ('여행' in raw or '투어' in raw or '축제' in raw): continue
        m = re.search(r'(?<!\d)(\d{1,3}(?:,\d{3})*|\d{4,8})\s*원', raw)
        if not m: continue
        title_node = el.select_one('h2,h3,h4,[class*=title],[class*=name]')
        title = title_node.get_text(' ',strip=True) if title_node else ''
        if not title:
            # Prefer human-readable text before the price, removing category label.
            title = raw[:m.start()].strip()
            for region in REGIONS:
                if title.startswith(region): title=title[len(region):].strip()
        title = re.sub(r'\s+', ' ', title).strip()
        if not 5 <= len(title) <= 150 or title in ('추천 여행 상품','인기 여행상품'): continue
        price = int(m.group(1).replace(',',''))
        if not 0 < price <= 100_000_000: continue
        a = el.select_one('a[href]')
        href = a.get('href','') if a else ''
        # No inferred per-product URL; use verified official landing page if unavailable.
        if href.startswith('https://www.korail.com/tour/goods/'):
            link=href
        elif href.startswith('/tour/goods/'):
            link='https://www.korail.com'+href
        else:
            link=URL
        area=next((x for x in REGIONS if x in raw), '지역 확인 필요')
        candidates.append({'name':title,'month':0,'theme':'기차여행','area':area,
            'price':price,'source':'한국철도공사','url':link,
            'desc':'코레일 공식 홈페이지에 게시된 여행상품입니다. 실제 가격·출발일·승차역·판매 상태는 공식 예약 페이지에서 확인해 주세요.',
            'icon':'🚆','color':'green'})
    # De-duplicate nested containers; avoid matching generic site-wide blocks.
    unique={}
    for p in candidates:
        k=(p['name'],p['price'])
        if k not in unique or (unique[k]['url']==URL and p['url']!=URL):unique[k]=p
    return list(unique.values())


def sync(html=None):
    if html is None:
        req=Request(URL,headers={'User-Agent':'YeongdeungpoTravelGuide/0.1 (public informational site; contact site administrator)', 'Accept':'text/html'})
        with urlopen(req,timeout=25) as res:
            if res.status != 200: raise RuntimeError(f'HTTP {res.status}')
            if 'html' not in res.headers.get('Content-Type','').lower(): raise RuntimeError('Not HTML')
            html=res.read(2_000_001).decode('utf-8','replace')
            if len(html)>2_000_000: raise RuntimeError('Response too large')
    products=parse(html)
    if len(products)<3: raise RuntimeError(f'Only {len(products)} recognizable cards: preserving old data')
    payload={'source':URL,'retrieved':dt.datetime.now(dt.timezone.utc).isoformat(),
             'kind':'공개 페이지 HTML 자동 수집 (추천/인기 노출 상품에 한함)',
             'sync_status':'ok','scope':'홈페이지에서 식별 가능한 일부 상품; 전체 판매 목록 아님',
             'products':products}
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=ROOT,delete=False) as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)
        temp=Path(f.name)
    temp.replace(DEST)
    print(f'CRAWL OK: {len(products)} cards')

if __name__=='__main__':
    try:
        fixture=os.getenv('KORAIL_HTML_FIXTURE')
        sync(Path(fixture).read_text(encoding='utf-8') if fixture else None)
    except Exception as e:
        print(f'CRAWL FAILED: {e}; existing products.json unchanged',file=sys.stderr)
        sys.exit(1)
