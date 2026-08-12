"""SSC Oracle WebCenter list/detail collector."""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urlencode,urljoin,urlsplit,parse_qs
from bs4 import BeautifulSoup
from ..models import Attachment,CollectorError,CollectorResult,CollectorStatus,utc_now
from ..normalize import build_record,canonicalize_url,normalize_body,normalize_title,parse_source_date
from .base import CollectorParseError

class SSCCollector:
    source_name="SSC"
    def __init__(self,http,config:dict)->None:
        self.http=http; self.base_url=str(config["base_url"]); self.list_url=str(config["list_url"]); self.detail_path=str(config["detail_path"]); self.entities=tuple(config.get("entities",["BCG","Bamboo Capital","BCG Land"])); self.default_max_pages=int(config.get("max_pages",10))
    @staticmethod
    def parse_list(html:str,page_url:str)->list[str]:
        soup=BeautifulSoup(html,"lxml"); root=soup.select_one(".news-list, #list-news")
        if root is None: raise CollectorParseError("SSC WebCenter list marker is missing")
        urls=[]
        for link in root.select("a[href*='dDocName=']"):
            url=canonicalize_url(link["href"],page_url)
            if parse_qs(urlsplit(url).query).get("dDocName"): urls.append(url)
        return list(dict.fromkeys(urls))
    @staticmethod
    def parse_detail(html:str,page_url:str)->dict:
        soup=BeautifulSoup(html,"lxml"); root=soup.select_one("article, .detail-news, #detail-news")
        if root is None: raise CollectorParseError("SSC WebCenter detail marker is missing")
        title=root.select_one("h1,h2,.title"); when=root.select_one("time,.date"); body=root.select_one(".content,.body")
        if title is None or when is None or body is None: raise CollectorParseError("SSC detail title/date/body is missing")
        content=normalize_body(body.get_text("\n",strip=True)); attachments=[]
        for link in body.select("a[href]"):
            href=canonicalize_url(link["href"],page_url)
            if "GET_FILE" in href or re.search(r"\.(pdf|docx?|xlsx?)(?:$|\?)",href,re.I): attachments.append(Attachment(normalize_title(link.get_text(" ",strip=True)) or "Tệp đính kèm",href))
        return {"title":normalize_title(title.get_text(" ",strip=True)),"date":parse_source_date(when.get_text(" ",strip=True)),"content":content,"attachments":attachments}
    def collect(self,start_date:date,end_date:date,*,max_pages:int|None=None)->CollectorResult:
        limit=max_pages or self.default_max_pages; now=utc_now(); records=[]; errors=[]; visited=[]; list_success=False
        for page in range(1,limit+1):
            url=f"{self.list_url}?{urlencode({'page':page})}"
            try:
                response=self.http.get(url,archive_source=self.source_name); visited.append(response.url); response.raise_for_status(); details=self.parse_list(response.text,response.url); list_success=True
            except Exception as exc:
                errors.append(CollectorError("LIST_FETCH_OR_SCHEMA_FAILED",f"{type(exc).__name__}: {exc}",url)); break
            if not details: break
            for detail_url in details:
                try:
                    response=self.http.get(detail_url,archive_source=self.source_name); visited.append(response.url); response.raise_for_status(); item=self.parse_detail(response.text,response.url); context=f"{item['title']} {item['content']}"
                    if not any(re.search(rf"(?<![A-Za-z0-9]){re.escape(e)}(?![A-Za-z0-9])",context,re.I) for e in self.entities): continue
                    if not start_date<=item["date"]<=end_date: continue
                    company="BCG Land" if "bcg land" in context.lower() else "BCG"
                    records.append(build_record(published_date=item["date"],company=company,source=self.source_name,source_type="REGULATOR",title_original=item["title"],content_original=item["content"],url=detail_url,attachments=item["attachments"],collected_at=now))
                except Exception as exc: errors.append(CollectorError("DETAIL_FETCH_OR_SCHEMA_FAILED",f"{type(exc).__name__}: {exc}",detail_url))
        status=CollectorStatus.FAILED if not list_success else CollectorStatus.PARTIAL if errors else CollectorStatus.SUCCESS
        return CollectorResult(self.source_name,status,records,errors,(start_date,end_date),visited,now)