# 파일명: crawler.py
import os
import feedparser
import yaml
import sqlite3
from datetime import datetime

CONFIG_PATH = "config.yaml"
OUT_DIR = "out_md"
DB_PATH = "news.db"

def init_db():
    """SQLite DB 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            summary TEXT,
            source TEXT,
            pub_date TEXT
        )
    """)
    conn.commit()
    return conn

def save_to_db(conn, title, link, summary, source, pub_date):
    """DB 저장 (중복 방지: link 기준)"""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO news (title, link, summary, source, pub_date)
            VALUES (?, ?, ?, ?, ?)
        """, (title, link, summary, source, pub_date))
        conn.commit()
    except Exception as e:
        print(f"DB 저장 오류: {e}")

def update_home_md(date_str, time_str):
    """Home.md 갱신: 최신 뉴스 링크 맨 위 누적"""
    home_file = os.path.join(OUT_DIR, "Home.md")
    if os.path.exists(home_file):
        with open(home_file, "r", encoding="utf-8") as f:
            home_lines = f.readlines()
    else:
        home_lines = [
            "# 📰 IT 뉴스 위키 홈\n\n",
            "자동 수집된 IT 뉴스 아카이브입니다.\n\n",
            "## 📅 최근 뉴스\n"
        ]

    # Daily 링크 추가
    today_news_link = f"- [{date_str} {time_str}시 IT 뉴스 요약](Daily/{date_str}-{time_str}.md)\n"
    home_lines.insert(3, today_news_link)  # 최근 뉴스 섹션 바로 아래

    # Home.md 다시 쓰기
    with open(home_file, "w", encoding="utf-8") as f:
        f.writelines(home_lines)

def main():
    # 설정 불러오기
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    feeds = cfg.get("feeds", [])
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "Daily"), exist_ok=True)

    # 날짜/시간 기반 파일
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H")  # 09 or 18
    out_file = os.path.join(OUT_DIR, "Daily", f"{date_str}-{time_str}.md")

    # DB 연결
    conn = init_db()

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# {date_str} {time_str}시 IT 뉴스 요약\n\n")

        for feed_url in feeds:
            d = feedparser.parse(feed_url)
            source = d.feed.get("title", feed_url)

            f.write(f"## {source}\n\n")

            for entry in d.entries[:10]:
                title = entry.title
                link = entry.link
                summary = getattr(entry, "summary", "").strip()
                pub_date = getattr(entry, "published", now.strftime("%Y-%m-%d %H:%M"))

                if summary:
                    summary = " ".join(summary.split())[:200]  # 200자 제한
                else:
                    summary = "(요약 없음)"

                # DB 저장
                save_to_db(conn, title, link, summary, source, pub_date)

                # Markdown 작성
                f.write(f"- **{title}**\n")
                f.write(f"  - {summary}\n")
                f.write(f"  - [원문 링크]({link})\n\n")

    # Home.md 갱신
    update_home_md(date_str, time_str)

    print(f"✅ 저장 완료: {out_file}")

if __name__ == "__main__":
    main()
