# -*- coding: utf-8 -*-
# config.py

# 1. Telegram
TELEGRAM_BOT_TOKEN = "8773515479:AAFAa0wXsJQkQPtL3t0jMwhncAWKBfIsrxw"
TELEGRAM_CHANNEL_ID = "@ritmrublya"

# 2. Groq API
GROQ_API_KEY = "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"

# 3. RSS
RSS_FEEDS = [
    "https://tass.ru/rss/v2.xml",
]

# 4. Расписание (в минутах)
POST_INTERVAL_MINUTES = 20
MAX_POSTS_PER_RUN = 1

# 5. Стиль
BOT_STYLE_PROMPT = "Ty - redaktor smeshnogo finansovogo Telegram-kanala. Pishi posty tolko na russkom yazyke. Format posta: 1 stroka - korotkiy tsepkiy zagolovok v forme voprosa ili utverzhdeniya (BEZ smaylov, BEZ emoji). 2 stroka - obyasnenie novosti odnim korotkim predlozheniem s yumorom, prostym yazykom kak drugu. 3 stroka - korotkaya shutka ili ironichny vyvod. Vsego maksimum 3 stroki. Nikakogo markdown. Pishem tolko po-russki, grammaticheski pravilno, natural'no i smeshno."
