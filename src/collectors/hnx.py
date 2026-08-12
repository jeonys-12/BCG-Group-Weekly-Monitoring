"""HNX official issuer disclosure collector."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ..models import Attachment, CollectorError, CollectorResult, CollectorStatus, utc_now
from ..normalize import build_record, canonicalize_url, normalize_title, parse_source_date
from .base import CollectorParseError

@dataclass(frozen=True)
class HNXItem:
    published_date: date
    title: str
    detail_url: str
    attachment_url: str | None = None

class HNXCollector:
    source_name = "HNX"
    def __init__(self, http, config: dict) -> None:
        self.http=http; self.base_url=str(config["base_url"]); self.template=str(config["issuer_page_template"])
        self.post_url=urljoin(self.base_url, str(config["disclosure_page_path"])); self.tickers=list(config.get("tickers", ["BCG","BCR"])); self.default_max_pages=int(config.get("max_pages",10))

    @staticmethod
    def parse_page(html: str, page_url: str) -> tuple[str, list[HNXItem]]:
        soup=BeautifulSoup(html,"lxml")
        market=soup.select_one("input[name=MarketCode], #MarketCode")
        if market is None or not market.get("value"): raise CollectorParseError("HNX MarketCode is missing")
        root=soup.select_one("#divViewThongTinCongBo, .issuer-disclosures")
        if root is None: raise CollectorParseError("HNX disclosure container is missing")
        items=[]
        for row in root.select(".news-item, tr[data-disclosure]"):
            link=row.select_one("a.detail[href], a[href*='chi-tiet']"); when=row.select_one(".date, time")
            if link is None or when is None: raise CollectorParseError("HNX disclosure row is missing date or detail URL")
            attachment=row.select_one("a.attachment[href]")
            items.append(HNXItem(parse_source_date(when.get_text(" ",strip=True)), normalize_title(link.get_text(" ",strip=True)), canonicalize_url(link["href"],page_url), canonicalize_url(attachment["href"],page_url) if attachment else None))
        return str(market["value"]),items

    def collect(self,start_date:date,end_date:date,*,max_pages:int|None=None)->CollectorResult:
        limit=max_pages or self.default_max_pages; now=utc_now(); records=[]; errors=[]; visited=[]; successes=0
        for ticker in self.tickers:
            url=self.template.format(ticker=ticker)
            try:
                response=self.http.get(url,archive_source=self.source_name); visited.append(response.url); response.raise_for_status(); market,items=self.parse_page(response.text,response.url); successes+=1
                seen={hashlib.sha256(response.content).hexdigest()}
                for page in range(2,limit+1):
                    response=self.http.post_form(self.post_url,data={"StockCode":ticker,"MarketCode":market,"Page":str(page)},archive_source=self.source_name); visited.append(response.url); response.raise_for_status()
                    digest=hashlib.sha256(response.content).hexdigest()
                    if not response.text.strip() or digest in seen: break
                    seen.add(digest); page_market,page_items=self.parse_page(response.text,response.url)
                    if page_market != market: raise CollectorParseError("HNX MarketCode changed during pagination")
                    if not page_items: break
                    items.extend(page_items)
                for item in items:
                    if start_date <= item.published_date <= end_date:
                        attachments=[Attachment("Tệp đính kèm",item.attachment_url)] if item.attachment_url else []
                        records.append(build_record(published_date=item.published_date,company=ticker,source=self.source_name,source_type="EXCHANGE",title_original=item.title,content_original=item.title,url=item.detail_url,attachments=attachments,collected_at=now))
            except Exception as exc:
                errors.append(CollectorError("TICKER_FETCH_OR_PARSE_FAILED",f"{type(exc).__name__}: {exc}",url))
        status=CollectorStatus.FAILED if successes==0 else CollectorStatus.PARTIAL if errors else CollectorStatus.SUCCESS
        return CollectorResult(self.source_name,status,records,errors,(start_date,end_date),visited,now)
