#!/usr/bin/env python3
"""Compatibility export of timestamped media leads; real --hours filtering, no browser."""
import argparse,json
from pathlib import Path
from chai_news_radar import ROOT,snapshot

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--json',type=Path,default=Path('/tmp/ai-media.json'))
    ap.add_argument('--hours',type=int,default=48)
    ap.add_argument('--refresh',action='store_true')
    a=ap.parse_args()
    if a.hours<=0:ap.error('hours must be positive')
    config=json.loads((ROOT/'workflows/chai-news-radar-sources.json').read_text())
    config['sources']=[s for s in config['sources'] if s['role']=='media_lead']
    data=snapshot(config,Path.home()/'.agent-reach/chai-news-radar',a.hours,a.refresh)
    rows=[dict(r,hint=r['published_at']) for r in data['candidates']]
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print(json.dumps({'leads':len(rows),'excluded':data['excluded'],'source_health':data['source_health'],'path':str(a.json)},ensure_ascii=False,indent=2))
    return 0 if any(s['status']=='ok' for s in data['source_health']) else 1

if __name__=='__main__':raise SystemExit(main())
