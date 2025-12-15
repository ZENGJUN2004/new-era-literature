import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io
import datetime
import re

# 1. 基础环境
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
MAX_DAYS_AGO = 2  # 只看最近 2 天

def get_header():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

# 2. 时间清洗器 (保持严厉的过滤逻辑)
def parse_baidu_time(time_str):
    now = datetime.datetime.now()
    time_str = str(time_str).strip()
    try:
        if "分钟前" in time_str:
            mins = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(minutes=mins)
        elif "小时前" in time_str:
            hours = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(hours=hours)
        elif "昨天" in time_str:
            return now - datetime.timedelta(days=1)
        elif "天前" in time_str:
            days = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(days=days)
        elif "年" in time_str or "-" in time_str:
            clean_str = time_str.replace("年", "-").replace("月", "-").replace("日", "")
            return datetime.datetime.strptime(clean_str, "%Y-%m-%d")
        else:
            return now # 默认算最新
    except:
        return now - datetime.timedelta(days=365)

# 3. 智能内容分类 (按用户需求重新定义)
def auto_classify(title):
    t = title.lower()
    # 核心关注：作品与作家
    if any(k in t for k in ['新书', '首发', '小说', '目录', '上市', '出版', '连载', '选载']):
        return 'activity' # 这里对应前端的“活动/动态”，实际指“作品动态”
    # 核心关注：思潮与话题
    if any(k in t for k in ['思潮', '热点', '争议', '现象', '非虚构', '科幻', '女性写作', 'ai写作', '排行榜']):
        return 'voice'    # 这里对应前端的“声音/观点”，实际指“话题”
    # 核心关注：批评与研究
    if any(k in t for k in ['评论', '批评', '研讨', '综述', '论', '读后感', '笔谈', '讲座']):
        return 'meeting'  # 这里对应前端的“会议/学术”，实际指“研究”
    return 'other'

# ==========================================
# 4. 全新战略：三大内容战区
# ==========================================
SEARCH_ZONES = [
    # 战区A：知名作家与重磅作品 (盯着“谁出了什么书”)
    {
        "name": "新作首发",
        "keywords": [
            "长篇小说 首发", "作家 新书发布", "文学期刊 目录", 
            "《收获》目录", "《十月》杂志", "《人民文学》", 
            "茅盾文学奖 作家", "鲁迅文学奖 得主 新书"
        ]
    },
    # 战区B：文学思潮与热点话题 (盯着“圈里在吵什么”)
    {
        "name": "思潮热点",
        "keywords": [
            "文学圈 热点", "文学 争议", "非虚构写作 讨论", 
            "科幻文学 趋势", "女性文学 话题", "当代文学 现象",
            "豆瓣读书 高分", "文学年度榜单"
        ]
    },
    # 战区C：批评家与深度观察 (盯着“专家怎么看”)
    {
        "name": "批评争鸣",
        "keywords": [
            "文学评论家 发声", "文学研讨会 综述", "当代文学批评", 
            "陈晓明 文学", "戴锦华 访谈", "李敬泽 观点", # 举例几位活跃的批评家
            "中国当代文学研究会", "学术月刊 文学"
        ]
    }
]

def fetch_zone_news(zone):
    print(f"正在深挖内容：[{zone['name']}] ...")
    zone_pool = []
    
    for kw in zone['keywords']:
        # rtt=1 强制按时间排序
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={kw}"
        
        try:
            res = requests.get(url, headers=get_header(), timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('div', class_='result-op')
            if not items: items = soup.find_all('div', class_='result')
            
            for item in items:
                try:
                    title_tag = item.find('h3').find('a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    source = item.find('span', class_='c-color-gray').get_text(strip=True) if item.find('span', class_='c-color-gray') else "文学现场"
                    time_str = item.find('span', class_='c-color-gray2').get_text(strip=True) if item.find('span', class_='c-color-gray2') else ""

                    # 严格的时间过滤
                    real_time = parse_baidu_time(time_str)
                    if (datetime.datetime.now() - real_time).days > MAX_DAYS_AGO:
                        continue

                    category = auto_classify(title)
                    
                    if not any(n['title'] == title for n in zone_pool):
                        zone_pool.append({
                            "title": title, "url": link, "source": source, 
                            "time": time_str,
                            "timestamp": real_time,
                            "category": category
                        })
                except: continue
            time.sleep(1)
        except Exception as e:
            print(f"  [{kw}] 搜索中断: {e}")

    return zone_pool

def fetch_all():
    all_news = []
    for zone in SEARCH_ZONES:
        all_news.extend(fetch_zone_news(zone))
    
    # --- 关键补充：针对很难爬取的“深度内容”提供直达梯子 ---
    now = datetime.datetime.now()
    static_links = [
        {"title": "👉【微信深度】搜索“文学批评”公众号最新文章", "url": "https://weixin.sogou.com/weixin?type=2&query=文学批评", "source": "微信", "time": "实时", "timestamp": now, "category": "voice"},
        {"title": "👉【豆瓣读书】本周虚构类热门图书榜", "url": "https://book.douban.com/chart?subcat=F", "source": "豆瓣", "time": "本周", "timestamp": now, "category": "activity"},
        {"title": "👉【知网学术】“当代文学”最新核心期刊论文", "url": "https://scholar.baidu.com/scholar?q=当代文学&sc_ylo=2024&sort=sc_time", "source": "CNKI", "time": "实时", "timestamp": now, "category": "meeting"},
    ]
    
    final_list = static_links + all_news
    
    # 去重
    seen = set()
    unique_list = []
    for item in final_list:
        if item['title'] not in seen:
            unique_list.append(item)
            seen.add(item['title'])

    # 按时间倒序
    unique_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 清理字段
    for item in unique_list:
        del item['timestamp']
        
    return unique_list[:60]

def save(data):
    try:
        # 北京时间
        utc_now = datetime.datetime.utcnow()
        cst_now = utc_now + datetime.timedelta(hours=8)
        time_str = cst_now.strftime('%Y-%m-%d %H:%M')
        
        final_json = { "update_time": time_str, "news": data }
        
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(f"window.LIT_DATA = {json.dumps(final_json, ensure_ascii=False, indent=2)};")
        print(f"✅ 内容抓取完成，共 {len(data)} 条")
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    data = fetch_all()
    save(data)

