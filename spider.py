import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io
import datetime
import re

# 1. 基础环境设置
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 核心配置：只保留最近 48 小时内的信息 ---
MAX_DAYS_AGO = 2 

def get_header():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

# 2. 智能时间解析器 (把“5分钟前”转换成电脑能懂的时间)
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
        elif "前天" in time_str:
            return now - datetime.timedelta(days=2)
        elif "天前" in time_str:
            days = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(days=days)
        elif "年" in time_str or "-" in time_str:
            # 处理标准日期格式
            clean_str = time_str.replace("年", "-").replace("月", "-").replace("日", "")
            dt = datetime.datetime.strptime(clean_str, "%Y-%m-%d")
            # 如果没有具体时间，默认设为当天的 00:00
            return dt
        else:
            # 遇到“刚刚”或者无法识别的，默认算作最新
            return now
    except:
        # 如果解析失败，为了安全起见，算作旧新闻扔掉
        return now - datetime.timedelta(days=365)

# 3. 智能分类 (会议/声音/活动)
def auto_classify(title):
    t = title.lower()
    if any(k in t for k in ['研讨', '座谈', '论坛', '峰会', '年会', '会议', '致辞', '讲座']):
        return 'meeting'
    if any(k in t for k in ['专访', '对话', '谈', '说', '论', '序言', '读后感', '批评', '观点', '综述', '笔谈']):
        return 'voice'
    if any(k in t for k in ['发布', '揭晓', '颁奖', '启动', '征文', '大赛', '活动', '目录', '征稿']):
        return 'activity'
    return 'other'

# ==========================================
# 4. 四大搜索战区 (覆盖作协、高校、期刊、微信)
# ==========================================
SEARCH_ZONES = [
    # 战区A：作协与官方 (盯着中国作家网、各省作协)
    {
        "name": "作协动态",
        "keywords": ["中国作协", "鲁迅文学奖", "茅盾文学奖", "作协 研讨会", "作家协会 公示"],
        "extra_query": " site:chinawriter.com.cn" # 必杀技：只搜中国作家网
    },
    # 战区B：期刊与出版 (盯着各大文学期刊、新书)
    {
        "name": "期刊出版",
        "keywords": ["文学期刊 目录", "长篇小说选刊", "收获杂志", "人民文学", "当代作家评论", "新书发布会"],
        "extra_query": "" 
    },
    # 战区C：高校与学术 (盯着全国大学网站)
    {
        "name": "高校学术",
        "keywords": ["中文系 讲座", "文学院 会议", "比较文学 论坛", "数字人文 研讨", "创意写作"],
        "extra_query": " site:edu.cn" # 必杀技：只搜 .edu.cn 结尾的大学官网
    },
    # 战区D：全网热点 (补充搜索)
    {
        "name": "网络热点",
        "keywords": ["文学批评", "作家专访", "网络文学 排行榜"],
        "extra_query": ""
    }
]

def fetch_zone_news(zone):
    print(f"正在扫描战区：[{zone['name']}] ...")
    zone_pool = []
    
    for kw in zone['keywords']:
        # 核心修改：rtt=1 强制百度按时间排序 (Real-time)
        query = kw + zone['extra_query']
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={query}"
        
        try:
            res = requests.get(url, headers=get_header(), timeout=12)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            items = soup.find_all('div', class_='result-op')
            if not items: items = soup.find_all('div', class_='result')
            
            for item in items:
                try:
                    title_tag = item.find('h3').find('a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    source_node = item.find('span', class_='c-color-gray')
                    source = source_node.get_text(strip=True) if source_node else zone['name']
                    
                    time_node = item.find('span', class_='c-color-gray2')
                    time_str = time_node.get_text(strip=True) if time_node else ""

                    # --- 关键步骤：时间清洗 ---
                    # 1. 算出具体时间
                    real_time = parse_baidu_time(time_str)
                    # 2. 算出是几天前的
                    days_diff = (datetime.datetime.now() - real_time).days
                    
                    # 3. 这里的逻辑：如果超过 2 天，直接扔掉！
                    if days_diff > MAX_DAYS_AGO:
                        continue

                    category = auto_classify(title)
                    
                    # 去重并加入列表
                    if not any(n['title'] == title for n in zone_pool):
                        zone_pool.append({
                            "title": title, "url": link, "source": source, 
                            "time": time_str,     # 显示用的时间字符串
                            "timestamp": real_time, # 排序用的时间对象
                            "category": category
                        })
                except:
                    continue
            time.sleep(1) # 礼貌延时
        except Exception as e:
            print(f"  搜索[{kw}]出错: {e}")

    return zone_pool

def fetch_all():
    all_news = []
    # 1. 扫描所有战区
    for zone in SEARCH_ZONES:
        news = fetch_zone_news(zone)
        all_news.extend(news)
    
    # 2. 补充很难爬取的平台（知网、微信）为固定直达入口
    # 这些平台反爬虫极严，直接爬会封IP，用“直达搜索链接”是最优解
    now = datetime.datetime.now()
    static_links = [
        {"title": "👉【微信搜狗】“文学评论”公众号最新文章 (点击直达)", "url": "https://weixin.sogou.com/weixin?type=2&query=文学评论", "source": "微信矩阵", "time": "实时", "timestamp": now, "category": "voice"},
        {"title": "👉【知网】“数字人文”最新学术论文 (按时间排序)", "url": "https://scholar.baidu.com/scholar?q=数字人文&sc_ylo=2024&as_ylo=2025&sort=sc_time", "source": "CNKI/学术", "time": "实时", "timestamp": now, "category": "meeting"},
        {"title": "👉【B站】文学讲座最新视频实录", "url": "https://search.bilibili.com/all?keyword=文学讲座&order=pubdate", "source": "Bilibili", "time": "实时", "timestamp": now, "category": "activity"},
    ]
    
    # 3. 合并数据
    final_list = static_links + all_news
    
    # 4. 再次按标题去重
    seen = set()
    unique_list = []
    for item in final_list:
        if item['title'] not in seen:
            unique_list.append(item)
            seen.add(item['title'])

    # 5. 最终排序：按时间倒序（最新的排最前面）！！！
    unique_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 6. 删除 timestamp 字段（不需要传给前端）
    for item in unique_list:
        del item['timestamp']
        
    return unique_list[:60] # 只保留最新的60条

def save(data):
    try:
        # 调整为北京时间显示
        utc_now = datetime.datetime.utcnow()
        cst_now = utc_now + datetime.timedelta(hours=8)
        time_str = cst_now.strftime('%Y-%m-%d %H:%M')
        
        # 变量名保持 LIT_DATA，不用改 HTML
        final_json = {
            "update_time": time_str,
            "news": data
        }
        
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(f"window.LIT_DATA = {json.dumps(final_json, ensure_ascii=False, indent=2)};")
            
        print("-" * 30)
        print(f"✅ 抓取完成！时间: {time_str}，共 {len(data)} 条新鲜资讯")
        
    except Exception as e:
        print(f"Save Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    data = fetch_all()
    save(data)
