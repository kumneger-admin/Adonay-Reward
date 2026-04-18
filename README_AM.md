# Adonay Reward Telegram Bot

**Adonay Reward** ለኢትዮጵያ ተጠቃሚዎች የተዘጋጀ የGiveaway, Invite እና Referral Telegram bot ፕሮጀክት ነው። ሁሉም የተጠቃሚ መልዕክቶች በአማርኛ ተዘጋጅተዋል።

## ዋና ባህሪያት

- **Database System** ከ8 ሙሉ ሰንጠረዦች ጋር
- **Force Join/Start** ተጠቃሚው ከመሳተፉ በፊት የግዴታ ቻናሎችን መቀላቀል
- **Profile Management** ፕሮፋይል እና ስታትስ
- **Daily Bonus** በስትሪክ የሚጨምር ዕለታዊ ሽልማት
- **Leaderboard** በባላንስ፣ ሪፈራል፣ ስትሪክ እና ተግባር ላይ የተለያዩ ደረጃዎች
- **Task System** እስከ 5 ንቁ የTelegram channel tasks ከማረጋገጫ ጋር
- **Withdrawal System** ለTeleBirr, CBE Birr እና Bank Transfer የmanual processing ስርዓት
- **Admin Panel** ስታትስ፣ ወጪ ጥያቄ፣ ቻናል አክል፣ ተግባር አክል፣ giveaway ፍጠር፣ broadcast

## Database Tables (8)

1. `users`
2. `channels`
3. `channel_tasks`
4. `task_completions`
5. `giveaways`
6. `giveaway_entries`
7. `withdrawals`
8. `daily_bonus_claims`

## የፕሮጀክት ፋይሎች

- `app.py` - ዋና የbot ሎጂክ
- `config.py` - ኮንፊግ
- `db.py` - SQLite database logic
- `keyboards.py` - ቁልፍ ሰሌዳዎች
- `states.py` - FSM states
- `schema.sql` - database schema
- `.env.example` - የenvironment variables ምሳሌ
- `requirements.txt` - dependencies

## መጫኛ እና አስጀማሪ መመሪያ

### 1) ፋይሎቹን ክፈት
```bash
unzip adonay-reward-bot.zip
cd adonay_reward_bot
```

### 2) የvirtual environment ፍጠር
```bash
python -m venv venv
source venv/bin/activate
```

### 3) dependencies ጫን
```bash
pip install -r requirements.txt
```

### 4) `.env` ፋይል ፍጠር
`.env.example` ን `.env` ብለው ይቀይሩ።

**ማሳሰቢያ:**
- `BOT_TOKEN` የBotFather token ይሁን
- `ADMIN_IDS` የአስተዳዳሪ Telegram user id ይሁን
- `BOT_USERNAME` የbot username ይሁን

### 5) bot አስነሳ
```bash
python app.py
```

## አስፈላጊ ማስታወሻዎች

- ቦቱ በforce join እና task verification እንዲሰራ በቻናሎች ውስጥ **admin** መሆን አለበት።
- ንቁ ተግባሮች ከፍተኛ ቁጥር **5** ነው።
- የwithdrawal ጥያቄ በuser ሲላክ ብሩ ከbalance ላይ ይቀነሳል። አስተዳዳሪ ካልፈቀደ ወደ balance ይመለሳል።
- giveaway winner selection ከፈለጉ በሚቀጥለው ስሪት ላይ random winner picker መጨመር ይቻላል።
- ይህ ፕሮጀክት MVP መሠረት ነው፤ ለproduction ውስጥ PostgreSQL, Redis, webhook, audit log, pagination, background jobs እና enhanced security መጨመር ይመከራል።

## አስተዳዳሪ የስራ ፍሰት

1. `/admin` ይክፈቱ
2. የforce join channels ያክሉ
3. በተፈለገው channel ላይ task ያክሉ
4. giveaway ፍጠሩ
5. pending withdrawals ን approve/reject ያድርጉ
6. ካስፈለገ broadcast ይላኩ

## የተጠቃሚ ስራ ፍሰት

1. `/start`
2. force join ያጠናቅቁ
3. daily bonus ይውሰዱ
4. 5 ተግባሮችን ያጠናቅቁ
5. ሪፈራል ሊንክ ያጋሩ
6. balance ካደገ በኋላ withdrawal ይጠይቁ

ከፈለጉ ቀጣይ ደረጃ ላይ webhook version, PostgreSQL version, Docker setup, deployment guide, anti-fraud system እና random giveaway winner module መጨመር እችላለሁ።

