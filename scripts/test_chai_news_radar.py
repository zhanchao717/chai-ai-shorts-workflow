#!/usr/bin/env python3
"""Verify time/coverage/cache failures that would otherwise pollute the topic pool."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import chai_news_radar as radar


def main():
    cases=[]
    def test(name,fn):
        fn();cases.append({"name":name,"status":"PASS"})
    as_of=radar.parse_date("2026-10-01T22:30:00+08:00")
    def dates():
        rows=[{"title":"recent","url":"https://example.com/recent","published_at":"Thu, 01 Oct 2026 10:00:00 GMT"},
              {"title":"old title says 刚刚","url":"https://example.com/old","published_at":"2026-09-28T10:00:00Z"},
              {"title":"future","url":"https://example.com/future","published_at":"2026-10-02T00:00:00+08:00"},
              {"title":"unknown timezone","url":"https://example.com/no-tz","published_at":"2026-10-01T10:00:00"}]
        recent,unknown,excluded=radar.filter_rows(rows,as_of,48,{})
        assert [r["title"] for r in recent]==["recent"]
        assert [r["title"] for r in unknown]==["unknown timezone"]
        assert excluded=={"stale":1,"future":1,"duplicate":0}
        assert recent[0]["event_published_at"] is None and recent[0]["event_time_verified"] is False
    test("real_48h_filter_future_and_unknown_time",dates)
    def urls():
        assert radar.canonical_url("https://aiera.com.cn/asi-item.html?id=a&utm_source=test#top")=="https://aiera.com.cn/asi-item.html?id=a"
        assert radar.canonical_url("https://aiera.com.cn/asi-item.html?id=a")!=radar.canonical_url("https://aiera.com.cn/asi-item.html?id=b")
    test("article_ids_preserved_tracking_removed",urls)
    def duplicate():
        rows=[{"title":"same","url":"https://example.com/a?utm_source=a","source":"媒体甲","published_at":"2026-10-01T12:00:00+08:00"},
              {"title":"same","url":"https://example.com/a?utm_source=b","source":"媒体乙","published_at":"2026-10-01T12:00:00+08:00"}]
        recent,_,excluded=radar.filter_rows(rows,as_of,48,{"https://example.com/a":{"first_seen_at":"2026-10-01T11:00:00+08:00"}})
        assert len(recent)==1 and excluded["duplicate"]==1
        assert recent[0]["also_seen_in"]==["媒体乙"] and recent[0]["seen_before"] is True
        assert recent[0]["first_seen_at"]=="2026-10-01T11:00:00+08:00"
    test("same_url_cross_source_evidence_and_first_seen",duplicate)
    def atom():
        xml='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Fresh</title><link href="https://example.com/post"/><published>2026-10-01T10:00:00Z</published></entry></feed>'
        assert radar.parse_rss(xml)[0]["url"]=="https://example.com/post"
    test("atom_feed_supported",atom)
    def media():
        blob=json.dumps({"own":{"s":"新智元","t":"报道","ymd":"2026-10-01","hm":"07:41","d":[]},
                         "other":{"s":"别的媒体","t":"新闻","ymd":"2026-10-01","hm":"09:00"}})
        rows=radar.parse_aiera(blob)
        assert len(rows)==1 and rows[0]["published_at"]=="2026-10-01T07:41:00+08:00"
    test("aiera_own_publisher_and_timezone",media)
    def reference():
        links=radar.primary_links('参考 https://manus.im/zh-cn/blog/introducing-manus-2-0 图片 https://blog.google/a.png https://unrelated.example/x', ['manus.im','blog.google'])
        assert links==['https://manus.im/zh-cn/blog/introducing-manus-2-0']
    test("primary_reference_candidates_exclude_images",reference)
    class Headers:
        def get_content_charset(self):return "utf-8"
    class Response:
        headers=Headers()
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,n):return b'<rss><channel><item><title>Fresh</title><link>https://example.com/x</link><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    def cache():
        with tempfile.TemporaryDirectory() as t:
            with patch.object(radar.urllib.request,'urlopen',return_value=Response()) as request:
                a,first=radar.read_public('https://example.com/feed',Path(t))
                b,second=radar.read_public('https://example.com/feed',Path(t))
                assert a==b and request.call_count==1
                assert first['mode']=='network' and second['mode']=='cache' and second['network_requests']==0
                assert first['fetched_at']==second['fetched_at']
    test("cache_avoids_repeat_request_and_keeps_original_time",cache)
    def outage():
        config={'sources':[{'id':'missing','name':'测试源','kind':'rss','role':'media_lead','url':'https://example.com/feed','enabled':True}]}
        with tempfile.TemporaryDirectory() as t:
            with patch.object(radar.urllib.request,'urlopen',side_effect=OSError('offline')):
                result=radar.snapshot(config,Path(t),as_of=as_of)
                assert result['source_health'][0]['status']=='failed' and result['candidates']==[]
                assert result['ready_to_script'] is False
    test("outage_visible_and_no_fake_empty_success",outage)
    def diversity():
        rows=[{'source_id':s,'source':s,'title':f'{s}-{i}','url':f'https://example.com/{s}/{i}','evidence_status':'media_unverified','published_at':'2026-10-01T12:00:00+08:00'} for s in ['fast','slow'] for i in range(6)]
        text=radar.report_md({'as_of':as_of.isoformat(),'window_hours':48,'source_health':[],'candidates':rows,'unknown_time_queue':[],'excluded':{}},12,3)
        assert 'fast-2' in text and 'fast-3' not in text and 'slow-2' in text and 'slow-3' not in text
    test("brief_does_not_get_flooded_by_one_media",diversity)
    result={'status':'PASS','cases':cases,'live_network_test':False,'publishing_test':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
