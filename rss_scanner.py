"""
RSS News & Web Content Scanner for Automated Shorts (Items 1, 57)
Fetches breaking news from RSS feeds and formats them into ready-to-produce video topics.
"""
import xml.etree.ElementTree as ET
import urllib.request
import re
from typing import List, Dict, Any

# Popular news & tech RSS feeds
DEFAULT_RSS_FEEDS = {
    "aa_guncel": {"name": "Anadolu Ajansı - Güncel", "url": "https://www.aa.com.tr/tr/rss/default?cat=guncel"},
    "ntv_son_dakika": {"name": "NTV - Son Dakika", "url": "https://www.ntv.com.tr/son-dakika.rss"},
    "bbc_turkce": {"name": "BBC Türkçe", "url": "http://feeds.bbci.co.uk/turkce/rss.xml"},
    "webtekno": {"name": "Webtekno - Teknoloji", "url": "https://www.webtekno.com/rss.xml"},
    "shiftdelete": {"name": "ShiftDelete - Teknoloji", "url": "https://shiftdelete.net/feed"},
    "coin_turk": {"name": "CoinTürk - Kripto Para", "url": "https://coin-turk.com/feed"},
}

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and entities from RSS summaries."""
    if not raw_html:
        return ""
    clean = re.sub(r'<.*?>', '', raw_html)
    clean = clean.replace('&quot;', '"').replace('&amp;', '&').replace('&nbsp;', ' ').replace('&#39;', "'")
    return clean.strip()

def fetch_rss_feed(feed_url: str, max_items: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches an RSS feed and returns a list of news items.
    """
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    req = urllib.request.Request(feed_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
            root = ET.fromstring(content)
            
            # Look for <channel><item> or direct <item>
            channel = root.find("channel")
            raw_items = channel.findall("item") if channel is not None else root.findall("item")
            
            for item in raw_items[:max_items]:
                title_elem = item.find("title")
                desc_elem = item.find("description")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")
                
                title = clean_html(title_elem.text if title_elem is not None else "")
                desc = clean_html(desc_elem.text if desc_elem is not None else "")
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                pub = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""
                
                if title:
                    items.append({
                        "title": title,
                        "description": desc,
                        "link": link,
                        "published_at": pub,
                        "suggested_topic": f"Son Dakika: {title}"
                    })
    except Exception as e:
        print(f"  [RSS Scanner] Error fetching '{feed_url}': {e}")
        
    return items

def get_breaking_news_topics(source_key: str = "aa_guncel", max_items: int = 5) -> List[Dict[str, Any]]:
    """Fetches breaking news from configured default RSS feeds."""
    feed_info = DEFAULT_RSS_FEEDS.get(source_key, DEFAULT_RSS_FEEDS["aa_guncel"])
    return fetch_rss_feed(feed_info["url"], max_items=max_items)
