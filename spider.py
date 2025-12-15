import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io
import datetime

# 1. 基础设置
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_header():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

# 2. 智能分类器 (保持不变)
def auto_classify(title):
    t = title.lower()
    if any(k in t for k in ['研讨', '座谈', '论坛', '峰会', '年会', '会议', '致辞', '开幕', '讲座']):
        return 'meeting'
    if any(k in t for k in ['专访', '对话', '谈', '说', '论', '序言', '读后感', '批评', '观点', '综述', '笔谈']):
        return 'voice'
    if any(k in t for k in ['发布', '揭晓', '颁奖', '启动', '征文', '大赛', '活动', '目录', '征稿']):
        return 'activity'
    return 'other'

# ==========================================
# 3. 核心升级：四大搜索战区
# ==========================================
SEARCH_ZONES = [
    # 战区A：作协与官方 (盯着中国作家网、各省作协)
    {
        "name": "作协动态",
        "keywords": ["中国作协", "鲁迅文学奖", "茅盾文学奖", "作协 研讨会", "作家协会 公示"],
        "extra_query": " site:chinawriter.com.cn" # 专门搜中国作家网
    },
    # 战区B：期刊与出版 (盯着各大文学期刊、新书)
    {
        "name": "期刊出版",
        "keywords": ["文学期刊 目录", "长篇小说选刊", "收获杂志", "人民文学", "当代作家评论", "新书发布会", "文学征文"],
        "extra_query": "" 
    },
    # 战区C：高校与学术 (盯着 edu.cn 后缀的大学网站)
    {
        "name": "高校学术",
        "keywords": ["中文系 讲座", "文学院 会议", "比较文学 论坛", "数字人文 研讨", "创意写作"],
        "extra_query": " site:edu.cn" # 必杀技：只搜大学网站
    },
    # 战区D：微信与网络 (搜狗微信很难爬，我们用百度搜聚合内容)
    {
        "name": "网络热点",
        "keywords": ["文学评论 微信公众号", "作家专访 深度", "豆瓣读书 高分", "网络文学 排行榜"],
        "extra_query": ""
    }
]

def fetch_zone_news(zone):
    print(f"\n>>> 正在扫描战区：[{zone['name']}] ...")
    zone_pool = []
    
    for kw in zone['keywords']:
        # 组合搜索词：关键词 + 限定网站
        # 例如："中文系 讲座 site:edu.cn"
        query = kw + zone['extra_query']
        print(f"  - 搜索指令: {query}")
        
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={query}"
        
        try:
            res = requests.get(url, headers=get_header(), timeout=12)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            items = soup.find_all('div', class_='result-op')
            if not items: items = soup.find_all('div', class_='result')
            
            count = 0
            for item in items:
                try:
                    title_tag = item.find('h3').find('a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    # 获取来源
                    source_node = item.find('span', class_='c-color-gray')
                    source = source_node.get_text(strip=True) if source_node else zone['name']
                    
                    # 获取时间
                    time_node = item.find('span', class_='c-color-gray2')
                    pub_time = time_node.get_text(strip=True) if time_node else "近期"
                    
                    category = auto_classify(title)
                    
                    # 去重逻辑
                    if not any(n['title'] == title for n in zone_pool):
                        zone_pool.append({
                            "title": title, "url": link, "source": source, 
                            "time": pub_time, "category": category
                        })
                        count += 1
                except:
                    continue
            # print(f"    找到 {count} 条")
            time.sleep(1.5) # 稍微慢点，防止百度封锁
            
        except Exception as e:
            print(f"    搜索报错: {e}")

    return zone_pool[:15] # 每个战区取前15条

def fetch_all():
    all_news = []
    
    # 1. 循环扫描所有战区
    for zone in SEARCH_ZONES:
        news = fetch_zone_news(zone)
        all_news.extend(news)
    
    # 2. 插入“硬链接”：针对很难爬取的平台（知网、微信、社科网）
    # 直接提供跳转链接，让用户点过去看，这是最稳定的
    print("\n>>> 生成静态直达入口...")
    static_links = [
        {"title": "👉【微信搜狗】点击查看“文学评论”公众号最新文章", "url": "https://weixin.sogou.com/weixin?type=2&query=文学评论", "source": "微信矩阵", "time": "实时", "category": "voice"},
        {"title": "👉【中国社科网】文学理论前沿资讯", "url": "http://lit.cssn.cn/wx/", "source": "CSSN", "time": "实时", "category": "meeting"},
        {"title": "👉【知网】“数字人文”最新学术论文(点击按时间排序)", "url": "https://scholar.baidu.com/scholar?q=数字人文&sc_ylo=2024&as_ylo=2025", "source": "百度学术", "time": "实时", "category": "activity"},
    ]
    
    # 3. 混合并去重
    final_list = static_links + all_news
    
    # 简单的按标题去重（防止不同关键词搜到同一篇）
    seen = set()
    unique_list = []
    for item in final_list:
        if item['title'] not in seen:
            unique_list.append(item)
            seen.add(item['title'])
            
    return unique_list

def save(data):
    try:
        # 调整为北京时间
        utc_now = datetime.datetime.utcnow()
        cst_now = utc_now + datetime.timedelta(hours=8)
        time_str = cst_now.strftime('%Y-%m-%d %H:%M')
        
        final_json = {
            "update_time": time_str,
            "news": data
        }
        
        # 写入文件
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(f"window.LIT_DATA = {json.dumps(final_json, ensure_ascii=False, indent=2)};")
            
        print("-" * 30)
        print(f"✅ 抓取完成！共收集 {len(data)} 条数据")
        print(f"时间已校准为: {time_str}")
        
    except Exception as e:
        print(f"Save Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    data = fetch_all()
    save(data)
