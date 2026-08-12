"""HOSE official public news API collector."""
from __future__ import annotations
import hashlib
from datetime import date
from urllib.parse import urlencode, urljoin
from ..models import Attachment, CollectorError, CollectorResult, CollectorStatus, utc_now
from ..normalize import build_record, canonicalize_url, normalize_title, parse_source_date
from .base import CollectorParseError

class HOSECollector:
    source_name="HOSE"
    def __init__(self,http,config:dict)->None:
        self.http=http; self.base_url=str(config["base_url"]); self.api=str(config["api_base_url"]); self.path=str(config.get("disclosure_path","/news/cate")); self.alias=str(config.get("category_alias","thong-tin-cong-bo")); self.tickers=tuple(config.get("tickers",["BCG"])); self.size=int(config.get("page_size",20)); self.default_max_pages=int(config.get("max_pages",10))
    @staticmethod
    def parse_payload(payload:dict)->tuple[list[dict],int|None]:
        if not isinstance(payload,dict) or payload.get("success") is not True or not isinstance(payload.get("data"),dict): raise CollectorParseError("HOSE API success/data schema is missing")
        data=payload["data"]; rows=data.get("items",data.get("rows"))
        if not isinstance(rows,list): raise CollectorParseError("HOSE API item list is missing")
        total=data.get("totalCount",data.get("total")); return rows,int(total) if total is not None else None
    def collect(self,start_date:date,end_date:date,*,max_pages:int|None=None)->CollectorResult:
        limit=max_pages or self.default_max_pages; now=utc_now(); records=[]; errors=[]; visited=[]; seen=set(); successes=0
        for page in range(1,limit+1):
            query=urlencode({"pageIndex":page,"pageSize":self.size,"startDate":start_date.isoformat(),"endDate":end_date.isoformat(),"aliasCate":self.alias,"title":"BCG"}); url=f"{self.api}{self.path}?{query}"
            try:
                response=self.http.get(url,headers={"Accept":"application/json"},archive_source=self.source_name); visited.append(response.url); response.raise_for_status()
                if "json" not in response.headers.get("Content-Type","").lower(): raise CollectorParseError("HOSE API did not return JSON")
                rows,total=self.parse_payload(response.json()); successes+=1; digest=hashlib.sha256(response.content).hexdigest()
                if digest in seen: break
                seen.add(digest)
                for row in rows:
                    title=normalize_title(str(row.get("title",row.get("name","")))); text=" ".join(str(row.get(k,"")) for k in ("securityCode","issuer","title","content"))
                    if not title or not any(t.lower() in text.lower() for t in self.tickers): continue
                    published=parse_source_date(str(row.get("publishDate",row.get("publishedDate","")))); detail=row.get("url") or urljoin(self.base_url,f"/vi/thong-tin-cong-bo/{row.get('id','')}")
                    attachments=[]
                    for item in row.get("attachments",[]) or []:
                        if item.get("url"): attachments.append(Attachment(str(item.get("name","Tệp đính kèm")),canonicalize_url(item["url"],self.base_url)))
                    records.append(build_record(published_date=published,company="BCG",source=self.source_name,source_type="EXCHANGE",title_original=title,content_original=str(row.get("content",title)),url=detail,base_url=self.base_url,document_number=row.get("number"),attachments=attachments,collected_at=now))
                if not rows or (total is not None and page*self.size>=total) or len(rows)<self.size: break
            except Exception as exc:
                errors.append(CollectorError("API_FETCH_OR_SCHEMA_FAILED",f"{type(exc).__name__}: {exc}",url)); break
        status=CollectorStatus.FAILED if successes==0 else CollectorStatus.PARTIAL if errors else CollectorStatus.SUCCESS
        return CollectorResult(self.source_name,status,records,errors,(start_date,end_date),visited,now)