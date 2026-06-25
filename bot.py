# -*- coding: utf-8 -*-
import re
import sqlite3
import logging
import time
import schedule
import requests
import feedparser
from datetime import datetime
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    GROQ_API_KEY,
    RSS_FEEDS,
    POST_INTERVAL_HOURS,
    MAX_POSTS_PER_RUN,
    BOT_STYLE_PROMPT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("/data/bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

DB_PATH = "/data/posted.db"
CURRENCY_MESSAGE_ID = 13


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS posted (url TEXT PRIMARY KEY, posted_at TEXT)")
    conn.commit()
    return conn


def is_posted(conn, url):
    return conn.execute("SELECT 1 FROM posted WHERE url=?", (url,)).fetchone() is not None


def mark_posted(conn, url):
    conn.execute(
        "INSERT OR IGNORE INTO posted (url, posted_at) VALUES (?, ?)",
        (url, datetime.utcnow().isoformat()),
    )
    conn.commit()


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    return text.strip()


def get_currency_rates():
    try:
        resp = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        usd = data["Valute"]["USD"]["Value"]
        eur = data["Valute"]["EUR"]["Value"]
        cny = data["Valute"]["CNY"]["Value"]
        date = data["Date"][:10]
        return (
            f"Курсы валют ЦБ РФ на {date}\n\n"
            f"Доллар США: {usd:.2f} руб.\n"
            f"Евро: {eur:.2f} руб.\n"
            f"Юань: {cny:.2f} руб.\n\n"
            f"@ritmrublya"
        )
    except Exception as e:
        log.error("Ошибка получения курсов: %s", e)
        return None


def update_currency_message():
    text = get_currency_rates()
    if not text:
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "message_id": CURRENCY_MESSAGE_ID, "text": text},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Курсы валют обновлены")
    except Exception as e:
        log.error("Ошибка обновления курсов: %s", e)


def fetch_news(conn):
    items = []
    for feed_url in RSS_FEEDS:
        log.info("Читаю фид: %s", feed_url)
        try:
            resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            resp.encoding = "utf-8"
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:20]:
                url = entry.get("link", "")
                if not url or is_posted(conn, url):
                    continue
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))[:600]
                if title:
                    items.append({"url": url, "title": title, "summary": summary})
        except Exception as e:
            log.warning("Ошибка фида %s: %s", feed_url, e)
    log.info("Новых новостей: %d", len(items))
    return items


def rewrite_with_groq(title, summary):
    user_message = (
        f"Заголовок: {title}\n\nКраткое содержание: {summary}\n\n"
        "Напиши пост для Telegram-канала на основе этой новости."
    )
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": BOT_STYLE_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 300,
                "temperature": 0.9,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("Ошибка Groq API: %s", e)
        return None


def send_to_telegram(text):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Пост отправлен")
        return True
    except Exception as e:
        log.error("Ошибка Telegram: %s", e)
        return False


def run():
    log.info("Запуск цикла")
    update_currency_message()
    conn = init_db()
    news_items = fetch_news(conn)
    posted_count = 0
    for item in news_items:
        if posted_count >= MAX_POSTS_PER_RUN:
            break
        log.info("Обрабатываю: %s", item["title"])
        post_text = rewrite_with_groq(item["title"], item["summary"])
        if not post_text:
            continue
        post_text = "\n\n".join(p.strip() for p in post_text.split("\n") if p.strip())
        post_text = "\n\n".join(p.strip() for p in post_text.split("\n") if p.strip())
        post_text += "\n\n@ritmrublya"
        if send_to_telegram(post_text):
            mark_posted(conn, item["url"])
            posted_count += 1
    log.info("Опубликовано: %d", posted_count)
    conn.close()


if __name__ == "__main__":
    log.info("Бот запущен. Интервал: каждые %d ч.", POST_INTERVAL_HOURS)
    run()
    schedule.every(20).minutes.do(run)
    while True:
        schedule.run_pending()
        time.sleep(30)
