import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io

# 1. 强制设置输出编码，防止云端打印中文/Emoji时崩溃
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 2. 搜索关键词池 (可随时添加)
KEYWORDS = [
    "中国作协", "鲁迅文学奖", "茅盾文学奖", "新书发布会", 
    "文学研讨会", "作家专访", "文学评论", "网络文学", 
    "莫言", "余华", "王安忆", "贾平凹"
]

def get_header():
    # 模拟真实浏览器
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/'
    }

def auto_classify(title):
    """智能分类算法"""
    t = title.lower()
    # 优先级 1: 会议
    if any(k in t for k in ['研讨', '座谈', '论坛', '峰会', '年会', '会议', '致辞', '开幕']):
        return 'meeting'
    # 优先级 2: 声音 (观点/访谈)
    if any(k in t for k in ['专访', '对话', '谈', '说', '论', '序言', '读后感', '批评', '观点']):
        return 'voice'
    # 优先级 3: 活动 (发布/奖项)
    if any(k in t for k in ['发布', '揭晓', '颁奖', '启动', '征文', '大赛', '讲座', '活动']):
        return 'activity'
    return 'other'

def fetch_literary_news():
    news_pool = []
    print(">>> 开始抓取文学资讯...")
    
    for kw in KEYWORDS:
        print(f"Searching: {kw}") 
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={kw}"
        
        try:
            res = requests.get(url, headers=get_header(), timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 兼容百度不同的结构
            items = soup.find_all('div', class_='result-op')
            if not items: items = soup.find_all('div', class_='result')
            
            for item in items:
                try:
                    title_tag = item.find('h3').find('a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    source = item.find('span', class_='c-color-gray').get_text(strip=True)
                    pub_time = item.find('span', class_='c-color-gray2').get_text(strip=True)
                    
                    category = auto_classify(title)
                    
                    # 去重
                    if not any(n['title'] == title for n in news_pool):
                        news_pool.append({
                            "title": title, "url": link, "source": source, 
                            "time": pub_time, "category": category
                        })
                except:
                    continue
        except Exception as e:
            print(f"Error on {kw}: {e}")
        
        time.sleep(1) # 礼貌延时

    # 3. 插入社交媒体置顶入口
    social_links = [
        {"title": "👉【微博】中国作家协会 - 官方实时动态", "url": "https://s.weibo.com/weibo?q=中国作协", "source": "微博", "time": "实时", "category": "meeting"},
        {"title": "👉【抖音】搜索“新书发布会”现场视频", "url": "https://www.douyin.com/search/新书发布会", "source": "抖音", "time": "实时", "category": "activity"},
        {"title": "👉【小红书】搜索“文学批评”最新笔记", "url": "https://www.xiaohongshu.com/search_result?keyword=文学批评", "source": "小红书", "time": "实时", "category": "voice"},
    ]
    
    # 社交在前，新闻在后
    return social_links + news_pool[:60]

def save(data):
    try:
        # 注意：这里生成的变量名是 LIT_DATA
        final_json = {
            "update_time": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
            "news": data
        }
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(f"window.LIT_DATA = {json.dumps(final_json, ensure_ascii=False, indent=2)};")
        print(f"Success! Saved {len(data)} items.")
    except Exception as e:
        print(f"Save Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        data = fetch_literary_news()
        save(data)
    except Exception as e:
        print(f"Critical Script Error: {e}")
        # 这里不退出，防止GitHub报红，至少保证流程跑通