#!/usr/bin/env python3
"""Timestamped official/media news leads, compact output, cached public reads. No publishing."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("Asia/Shanghai")


def now():
    return datetime.now(TZ)


def canonical_url(url):
    u = urlsplit(url)
    query = [(k,v) for k,v in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"from","fromurl","spm"}]
    return urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path.rstrip("/"),urlencode(query),""))


def parse_date(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        try:d = parsedate_to_datetime(value)
        except (ValueError, TypeError):return None
    # A missing timezone must not silently become an exact local timestamp.
    return d.astimezone(TZ) if d.tzinfo else None


def read_public(url, cache, ttl=600, refresh=False):
    key=hashlib.sha256(url.encode()).hexdigest()
    body, meta=cache/(key+".body"), cache/(key+".json")
    try:cached=json.loads(meta.read_text()) if meta.exists() else {}
    except (ValueError,OSError):cached={}
    if body.exists() and not refresh and time.time()-cached.get("fetched_epoch",0)<ttl:
        return body.read_text(),{"mode":"cache","fetched_at":cached["fetched_at"],"network_requests":0}
    request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; ChaiNewsRadar/2.2)","Accept":"application/rss+xml,application/json,text/html,*/*"})
    with urllib.request.urlopen(request,timeout=25) as response:
        data=response.read(3_000_001)
        if len(data)>3_000_000:raise ValueError("response exceeds 3MB metadata limit")
        text=data.decode(response.headers.get_content_charset() or "utf-8",errors="replace")
    cache.mkdir(parents=True,exist_ok=True)
    body.write_text(text)
    stamp=now().isoformat()
    meta.write_text(json.dumps({"url":url,"fetched_epoch":time.time(),"fetched_at":stamp}))
    return text,{"mode":"network","fetched_at":stamp,"network_requests":1}


def parse_rss(text):
    root=ET.fromstring(text);out=[]
    for x in root.findall(".//item"):
        title=x.findtext("title") or "";url=x.findtext("link") or ""
        if title and url:
            out.append({"title":unescape(title).strip(),"url":url,"published_at":x.findtext("pubDate"),"time_precision":"second"})
    if not out:
        ns={"a":"http://www.w3.org/2005/Atom"}
        for x in root.findall("a:entry",ns):
            link=next((l.get("href") for l in x.findall("a:link",ns) if l.get("rel","alternate")=="alternate"),None)
            if link:out.append({"title":x.findtext("a:title",default="",namespaces=ns),"url":link,
                               "published_at":x.findtext("a:published",namespaces=ns) or x.findtext("a:updated",namespaces=ns),"time_precision":"second"})
    return out


def parse_aiera(text):
    data=json.loads(text);out=[]
    for key,item in data.items():
        if not isinstance(item,dict) or item.get("s")!="新智元":continue
        day=item.get("ymd");hm=item.get("hm")
        stamp=f"{day}T{hm}:00+08:00" if day and hm else None
        out.append({"title":item.get("t",""),"url":"https://aiera.com.cn/asi-item.html?id="+key,
                    "published_at":stamp,"time_precision":"minute" if stamp else "unknown",
                    "reported_source":item.get("s"),"summary": " ".join(item.get("d",[]))[:120]})
    return out


class NewsLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.current=None;self.rows=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href","").startswith("/news/"):
            self.current={"url":urljoin("https://www.anthropic.com",a["href"]),"texts":[]}
    def handle_data(self,data):
        if self.current:self.current["texts"].append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.current:
            self.rows.append(self.current);self.current=None


def parse_anthropic(text):
    parser=NewsLinks();parser.feed(text)
    decoded=re.sub(r'\\+"','"',text)
    exact={slug:stamp for stamp,slug in re.findall(r'"publishedOn":"([^"]+)".{0,140}?"current":"([^"]+)"',decoded)}
    out=[];seen=set()
    for row in parser.rows:
        url=row["url"]
        if url in seen:continue
        seen.add(url);slug=url.rsplit("/",1)[-1]
        raw=" ".join(t.strip() for t in row["texts"] if t.strip())
        date_match=re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4}',raw)
        title=raw
        if date_match:title=raw[date_match.end():].strip() or raw[:date_match.start()].strip()
        title=re.sub(r'^(Announcements|Features|Science|Policy)\s*','',title)
        out.append({"url":url,"title":title[:180],"published_at":exact.get(slug),
                    "time_precision":"second" if slug in exact else "unknown",
                    "display_date":date_match.group(0) if date_match else None})
    return out


PARSERS={"rss":parse_rss,"aiera_json":parse_aiera,"anthropic_html":parse_anthropic}


def primary_links(text,hosts):
    out=[]
    for value in re.findall(r'https?://[^\s<>"\]\)]+',unescape(text)):
        value=value.rstrip("，。；,;.")
        u=urlsplit(value);host=u.hostname or ""
        if not any(host==h or host.endswith("."+h) for h in hosts):continue
        if re.search(r'\.(?:png|jpe?g|webp|gif|svg|mp4)(?:\?|$)',value,re.I):continue
        value=canonical_url(value)
        if value not in out:out.append(value)
    return out[:12]


def filter_rows(rows,as_of,hours,seen):
    recent, unknown, excluded=[],[],{"stale":0,"future":0,"duplicate":0}
    cutoff=as_of-timedelta(hours=hours)
    used={}
    for r in rows:
        if not r.get("title") or not r.get("url"):continue
        url=canonical_url(r["url"])
        if url in used:
            excluded["duplicate"]+=1
            source=r.get("source")
            if source and source not in used[url]["also_seen_in"]:used[url]["also_seen_in"].append(source)
            continue
        r=dict(r,url=url,also_seen_in=[])
        used[url]=r
        r["first_seen_at"]=seen.get(url,{}).get("first_seen_at") or as_of.isoformat()
        r["seen_before"]=url in seen
        r["evidence_status"]="official_unreviewed" if r.get("role")=="official_announcement" else "media_unverified"
        r["candidate_primary_links"]=[]
        r["event_published_at"]=None
        r["event_time_verified"]=False
        d=parse_date(r.get("published_at"))
        if not d:unknown.append(r);continue
        r["published_at"]=d.isoformat()
        if d>as_of:excluded["future"]+=1;continue
        if d<cutoff:excluded["stale"]+=1;continue
        recent.append(r)
    recent.sort(key=lambda x:x["published_at"],reverse=True)
    return recent,unknown,excluded


def snapshot(config,cache,hours=48,refresh=False,as_of=None,per_source=20):
    as_of=as_of or now();rows=[];health=[]
    def collect(source):
        if not source.get("enabled"):
            return [],{"source":source["name"],"status":"manual","note":source.get("note")}
        try:
            text,read=read_public(source["url"],cache,config.get("cache_ttl_seconds",600),refresh)
            entries=PARSERS[source["kind"]](text)
            values=[dict(r,source=source["name"],source_id=source["id"],role=source["role"],
                         collected_at=read["fetched_at"],read_mode=read["mode"]) for r in entries]
            return values,{"source":source["name"],"status":"ok" if entries else "empty",
                          "entries":len(entries),"url":source["url"],"note":source.get("note"),**read}
        except Exception as e:
            return [],{"source":source["name"],"status":"failed","error":type(e).__name__+": "+str(e)[:120]}
    cache.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        for values,status in pool.map(collect,config["sources"]):rows+=values;health.append(status)
    state=cache/"seen.json"
    try:seen=json.loads(state.read_text()) if state.exists() else {}
    except (ValueError,OSError):seen={}
    recent,unknown,excluded=filter_rows(rows,as_of,hours,seen)
    counts={};selected=[]
    for row in recent:
        key=row["source_id"];counts[key]=counts.get(key,0)+1
        if counts[key]<=per_source:selected.append(row)
    # Only observed non-future items update first-seen state. An outage never
    # re-labels cached old news as a fresh successful network read.
    for row in recent+unknown:seen[row["url"]]={"first_seen_at":row["first_seen_at"],"last_seen_at":as_of.isoformat()}
    state.write_text(json.dumps(seen,ensure_ascii=False,indent=2))
    return {"schema_version":1,"as_of":as_of.isoformat(),"window_hours":hours,
            "source_health":health,"candidates":selected,"unknown_time_queue":unknown[:20],"excluded":excluded,
            "selection":"recency_only_not_editorial_ranking","ready_to_script":False,
            "note":"榜单仅为线索。先阅读原文，核对主断言，填写观众/任务/证据/决定四项，再做编辑评分；不按星数或清单数量打分。"}


def report_md(data,limit,per_source=3):
    lines=["# 柴主编新闻雷达",f"\n运行时刻：{data['as_of']}；最近 {data['window_hours']} 小时。按时间列线索，未完成事实核验或选题拍板。",
           "\n## 信源健康", "\n| 信源 | 状态 / 读取方式 | 实际读取时刻 | 当前结果 |", "|---|---|---|---|"]
    for row in data["source_health"]:
        lines.append(f"| {row['source']} | {row['status']} / {row.get('mode','—')} | {row.get('fetched_at','—')} | {row.get('entries','—')} 条；{row.get('note',row.get('error',''))} |")
    lines += ["\n## 最近线索（最多给编导看的数量）", "\n| 标题 | 信源 / 证据状态 | 发布（北京时间） |", "|---|---|---|"]
    brief=[];counts={}
    for row in data["candidates"]:
        key=row["source_id"]
        if counts.get(key,0)>=per_source:continue
        brief.append(row);counts[key]=counts.get(key,0)+1
        if len(brief)>=limit:break
    for row in brief:
        title=row['title'].replace('|','／')
        lines.append(f"| [{title}]({row['url']}) | {row['source']} / {row['evidence_status']} | {row['published_at']} |")
    lines += [f"\n本简报最多每源 {per_source} 条，避免高频媒体挤满候选。发布时间未知另列 {len(data['unknown_time_queue'])} 条，不冒充今日消息。排除：{data['excluded']}。",
              "\n## 下一步", "\n1. 只深读最相关的 3 条，提取公司公告/论文/仓库/原始采访。",
              "2. 核对事件原始发布日期，再检查同一官方链接和已有作品/被否决选题；有重大新变化才做更新。媒体发稿时间不代替事件时间。",
              "3. 写清普通观众受何影响、现在能做什么、未开放/未实测的限制，再决定是否拍。"]
    return "\n".join(lines)+"\n"


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config",type=Path,default=ROOT/"workflows/chai-news-radar-sources.json")
    ap.add_argument("--hours",type=int,default=48)
    ap.add_argument("--limit",type=int,default=12)
    ap.add_argument("--per-source",type=int,default=20)
    ap.add_argument("--brief-per-source",type=int,default=3,help="cap each source in the editor brief; no popularity ranking")
    ap.add_argument("--cache-dir",type=Path,default=Path.home()/".agent-reach/chai-news-radar")
    ap.add_argument("--refresh",action="store_true")
    ap.add_argument("--as-of",help="optional timezone-aware timestamp for reproducible checks")
    ap.add_argument("--json",type=Path,default=Path("/tmp/chai-news-radar.json"))
    ap.add_argument("--report",type=Path,default=Path("/tmp/chai-news-radar.md"))
    ap.add_argument("--no-browser",action="store_true",help="compatibility flag; this radar uses only public reads")
    ap.add_argument("--inspect-url",help="read one selected article with Jina and list possible primary-source links")
    args=ap.parse_args()
    if min(args.hours,args.limit,args.per_source,args.brief_per_source)<=0:ap.error("hours/limits must be positive")
    config=json.loads(args.config.read_text())
    as_of=parse_date(args.as_of) if args.as_of else None
    if args.as_of and as_of is None:ap.error("as-of needs a valid explicit timezone")
    if args.inspect_url:
        if not args.inspect_url.startswith(("https://","http://")):ap.error("inspect-url must be an HTTP(S) URL")
        text,read=read_public("https://r.jina.ai/"+args.inspect_url,args.cache_dir,refresh=args.refresh)
        result={"url":args.inspect_url,"read":read,"candidate_primary_links":primary_links(text,config["primary_link_hosts"]),
                "evidence_status":"links_found_not_claims_verified","characters":len(text)}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    data=snapshot(config,args.cache_dir,args.hours,args.refresh,as_of,args.per_source)
    for p in (args.json,args.report):p.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    args.report.write_text(report_md(data,args.limit,args.brief_per_source))
    print(json.dumps({"as_of":data["as_of"],"recent_leads":len(data["candidates"]),"unknown_time":len(data["unknown_time_queue"]),
                      "excluded":data["excluded"],"source_health":data["source_health"],
                      "json":str(args.json),"report":str(args.report),"ready_to_script":False},ensure_ascii=False,indent=2))
    return 0 if any(x.get("status")=="ok" for x in data["source_health"]) else 1


if __name__=="__main__":raise SystemExit(main())
