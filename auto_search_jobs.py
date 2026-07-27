#!/usr/bin/env python3
"""
心理学硕士可投递岗位自动搜索脚本
每天运行一次，抓取高校人才网等平台的岗位信息，更新 job_announcements.json

运行方式: python3 auto_search_jobs.py
输出文件: ./job_announcements.json
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

# 配置
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_announcements.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 15

# 心理学相关关键词
KEYWORDS = ["心理学", "心理", "心理健康", "应用心理", "心理测量", "心理咨询"]


def search_gaoxiaojob():
    """搜索高校人才网 (gaoxiaojob.com)"""
    results = []
    base_url = "https://www.gaoxiaojob.com"

    for keyword in KEYWORDS[:3]:  # 只搜前3个关键词避免请求过多
        try:
            search_url = f"{base_url}/search?keyword={quote(keyword)}&type=announcement"
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".announcement-item, .job-item, .list-item")

            for item in items[:8]:
                try:
                    title_el = item.select_one("a.title, h3 a, .name a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin(base_url, url)

                    # 提取其他信息
                    org_el = item.select_one(".org, .company, .unit")
                    org = org_el.get_text(strip=True) if org_el else ""

                    loc_el = item.select_one(".location, .city, .area")
                    location = loc_el.get_text(strip=True) if loc_el else ""

                    deadline_el = item.select_one(".deadline, .time, .end-time")
                    deadline = deadline_el.get_text(strip=True) if deadline_el else ""

                    # 判断类别
                    category = "高校"
                    if "事业单位" in title or "事业编" in title:
                        category = "事业单位"
                    elif "国企" in title or "央企" in title:
                        category = "国企"

                    results.append({
                        "title": title,
                        "org": org or "详见公告",
                        "category": category,
                        "location": location or "详见公告",
                        "deadline": deadline or "详见公告",
                        "url": url,
                        "tags": ["心理学", category],
                        "is_open": True
                    })
                except Exception:
                    continue
        except Exception:
            continue
        time.sleep(0.5)

    return results


def search_gxrcyj():
    """搜索高校人才引进网 (gxrcyj.com)"""
    results = []
    base_url = "https://www.gxrcyj.com"

    for keyword in ["心理学", "心理健康"]:
        try:
            search_url = f"{base_url}/search?keyword={quote(keyword)}"
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li, .item, .list-item, article")

            for item in items[:8]:
                try:
                    title_el = item.select_one("a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if not any(kw in title for kw in ["心理", "招聘", "人才", "引进"]):
                        continue
                    url = title_el.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin(base_url, url)

                    results.append({
                        "title": title,
                        "org": "详见公告",
                        "category": "高校",
                        "location": "详见公告",
                        "deadline": "详见公告",
                        "url": url,
                        "tags": ["心理学"],
                        "is_open": True
                    })
                except Exception:
                    continue
        except Exception:
            continue
        time.sleep(0.5)

    return results


def is_recent_enough(deadline_str):
    """判断截止日期是否未过期或近1个月内"""
    if not deadline_str or "详见" in deadline_str or "待确认" in deadline_str:
        return True  # 无法判断，保留

    patterns = [
        (r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", "ymd"),
        (r"(\d{1,2})月(\d{1,2})日", "md"),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, deadline_str)
        if match:
            try:
                if fmt == "ymd":
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                else:
                    m, d = int(match.group(1)), int(match.group(2))
                    y = datetime.now().year
                deadline_date = datetime(y, m, d)
                if deadline_date < datetime.now() - timedelta(days=14):
                    return False
                return True
            except ValueError:
                continue
    return True


def load_existing():
    """加载已有公告数据"""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"announcements": [], "updated": "", "source": "auto-search"}


def merge_announcements(existing, new_results):
    """合并新旧公告，去重，保留手工添加的条目"""
    existing_urls = {a.get("url", "") for a in existing.get("announcements", [])}

    # 从新结果中过滤掉已存在的
    for result in new_results:
        url = result.get("url", "")
        if url and url not in existing_urls:
            existing["announcements"].insert(0, result)
            existing_urls.add(url)

    # 限制总数不超过50条
    existing["announcements"] = existing["announcements"][:50]

    return existing


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始搜索心理学相关岗位...")

    all_results = []

    # 搜索多个来源
    print("  搜索高校人才网...")
    results1 = search_gaoxiaojob()
    all_results.extend(results1)
    print(f"    找到 {len(results1)} 条")

    print("  搜索高校人才引进网...")
    results2 = search_gxrcyj()
    all_results.extend(results2)
    print(f"    找到 {len(results2)} 条")

    # 去重
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    print(f"  去重后共 {len(unique_results)} 条新公告")

    # 加载已有数据并合并
    existing = load_existing()
    existing["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    updated = merge_announcements(existing, unique_results)

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    total = len(updated.get("announcements", []))
    open_count = sum(1 for a in updated.get("announcements", []) if a.get("is_open", True))
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成！共 {total} 条公告（其中 {open_count} 条可投递）")
    print(f"  输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
