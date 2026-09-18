# Discord Bot with LLM — Project Requirements & Structure

> **Single source of truth** for purpose, requirements, architecture, and conventions.
> Prefer this document over inferring behavior from scattered comments or chat history.
> When code and this doc disagree, update **both** in the same change.

---

## 1. Purpose

A Discord bot for a private Japanese-speaking community that uses a **nursery / growth metaphor**:

| Role | Meaning |
|------|---------|
| **Infant** | New member (assigned on join) |
| **Toddler** | Member who has spoken in a public channel |
| **Parent** | Moderator / admin |

The bot:

1. **Chats with members** via Google Gemini when mentioned or via `!gem`.
2. **Manages the Infant → Toddler lifecycle** and logs milestones.
3. **Curates messages** into collection channels via emoji reactions.
4. **Engages Infants** with optional periodic check-ins (LLM-generated prompts).
5. **Provides Parent admin tools** (permission sync, message purge, prompt control).

It is designed for **one guild** (`GUILD_ID`). **Production hosting is on [Koyeb](https://app.koyeb.com/)** (Docker / `python main.py`). A Flask keep-alive endpoint (`keep_alive.py`, port 8080) remains for health checks. An older Render service (`discord-bot-with-llm.onrender.com`) exists but is **Suspended** and is not the live bot.

---

## 2. Non-goals (current)

- Multi-guild support
- OpenAI / Cohere as the active chat backend (keys may exist in config; Gemini is the live model)
- Production database usage (Postgres/pgvector scaffolding exists but is **disabled** — see §7)
- Public/self-serve bot listing

---

## 3. Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| Discord | `discord.py` ~= 2.3 (prefix `!` + app/slash commands) |
| LLM | Google Generative AI — model `gemini-2.0-flash-exp` |
| Config | `pydantic-settings` from `.env` |
| Keep-alive | Flask on `0.0.0.0:8080` |
| Hosting | **Koyeb** (primary); Render legacy suspended |
| DB (scaffold) | SQLAlchemy async + asyncpg + pgvector |
| Container | `dockerfile` → `python main.py` |

Dependencies: `requirements.txt`.

### Deploy notes (Koyeb)

- Live bot = Koyeb service env (especially `GEMINI_API_KEY`, `DISCORD_API_KEY`, `TYPESAFE_API_KEY`).
- GitHub OAuth to Koyeb may be used for login; confirm branch/commit in the Koyeb dashboard for auto-deploy.
- On Gemini `API_KEY_INVALID`, the bot replies in Japanese asking to refresh `GEMINI_API_KEY` on Koyeb (raw Google error text is not shown to users).
- On missing/invalid Jev key, `!運勢` replies asking to check `TYPESAFE_API_KEY` on Koyeb.
---

## 4. Repository structure

```
discord-bot-with-llm/
├── PROJECT.md              ← this document (SSOT)
├── main.py                 ← entry: keep_alive + DiscordBot
├── Config.py               ← Settings from .env
├── keep_alive.py           ← Flask “I'm alive” for uptime pings
├── requirements.txt
├── dockerfile
├── .env                    ← secrets (not committed)
├── src/
│   ├── DiscordBot.py       ← Bot subclass; loads cogs
│   ├── Logger.py           ← console logging factory
│   ├── Session.py          ← async SQLAlchemy session generator
│   ├── Entities.py         ← ORM models (Message + embedding column)
│   ├── Models.py           ← Pydantic DTOs (Message / MessagePayload)
│   ├── Repositories.py     ← generic CRUD repository
│   ├── Migrate.py          ← create_all table sync (manual)
│   ├── FortuneSchema.py    ← Jev 運勢 questions + state/result helpers
│   ├── JevClient.py        ← Async TypeSafe Jev wrapper
│   └── Cogs/
│       ├── Gemini.py       ← LLM chat, engagement, Parent tools
│       ├── Fortune.py      ← `!運勢` / `!fortune`
│       ├── RoleOperation.py← roles, reactions, slash admin
│       └── Utils.py        ← argument sanitization
```

### Responsibility map

| Module | Owns |
|--------|------|
| `main.py` | Process bootstrap; optional `migrate_tables()` (commented out) |
| `DiscordBot` | Intents, cog registration, token start |
| `RoleOperation` | Join/first-word roles, reaction curation, slash sync/shutdown |
| `Gemini` | Mentions / `!gem`, chat history context, periodic infant check, Parent utilities |
| `Fortune` | `!運勢` / `!fortune` via Jev |
| `Config` | Required env vars and channel/guild IDs |

---

## 5. Runtime & configuration

### Required environment variables

Defined in `Config.Settings` (loaded from `.env`):

| Variable | Purpose |
|----------|---------|
| `DISCORD_API_KEY` | Bot token |
| `GEMINI_API_KEY` | Google Generative AI |
| `TYPESAFE_API_KEY` | TypeSafe Jev（`!運勢`）。未設定でも起動可。コマンド実行時に日本語エラー |
| `OPENAI_API_KEY` | Present in settings; **not used** by current Gemini path |
| `INITIAL_PROMPT` | System-style seed for Gemini chat history |
| `LOG_CHANNEL_ID` | Join / first-word / shutdown notices |
| `GAKUBUCHI_CHANNEL_ID` | Destination for `🖼️` curated posts |
| `MINNA_BUNKO_CHANNEL_ID` | Destination for `minna_bunko` emoji |
| `FREEMEMO_CHANNEL_ID` | Destination for `📝` curated posts |
| `GUILD_ID` | Target server; slash commands sync here |

Commented / unused in settings: Postgres URLs, `IS_PROD`. `get_db_url()` currently returns `None`.

### Discord intents

- `message_content` — required for reading message text
- `members` — required for joins, roles, infant picking

### Hardcoded IDs / constants (code)

| Constant | Location | Meaning |
|----------|----------|---------|
| `BABY_ROOM_CATEGORY_ID` = `1150088658947407952` | `Gemini` | Category used for periodic check channel picks & default permission sync |
| Channel filter `1173806749757743134` | `Gemini.on_message` | Mentions in this channel are **ignored** for chat |

Prefer moving new IDs into `.env` rather than hardcoding.

### Start sequence

1. `keep_alive()` starts Flask in a background thread.
2. `asyncio.run(main())` → `DiscordBot().get_started()`.
3. `setup_hook` loads `RoleOperation` then `Gemini`.
4. Periodic infant check **starts stopped**; Parents enable with `!start_periodic_check`.

---

## 6. Domain requirements

### 6.1 Role lifecycle

1. **On member join** → assign **Infant**; post welcome to log channel (`Hello Baby!`).
2. **First non-empty message** by an Infant in a **public** text channel (no permission overwrites) → promote to **Toddler**, remove Infant, log with jump URL.
3. Bots and empty (mention-only) messages do not trigger promotion.
4. DM messages are ignored for role logic.

### 6.2 Message curation (reactions)

On **first** reaction of a mapped emoji (count must be exactly 1 when handled):

| Emoji / name | Destination env |
|--------------|-----------------|
| `🖼️` | `GAKUBUCHI_CHANNEL_ID` |
| custom name `minna_bunko` | `MINNA_BUNKO_CHANNEL_ID` |
| `📝` | `FREEMEMO_CHANNEL_ID` |

Behavior: embed with channel title + jump URL, author, optional first attachment image, footer “Collected by …”; mention original author in destination channel.

Listeners are restricted conceptually to Parent/Toddler (decorator present on the reaction handler).

### 6.3 LLM chat

**Triggers**

- Bot mention in a guild channel (except the ignored channel ID above), not from the bot itself.
- `!gem <text>` — roles: **Parent** or **Toddler**.

**Behavior**

- Build context from the last `MESSAGE_HISTORY_LIMIT` channel messages (default **50**, range 1–50 via `!set_history_limit`), excluding bot messages, oldest-first.
- Send to a persistent Gemini chat seeded with `INITIAL_PROMPT`.
- Reply; if content > 2000 chars, chunk (~1990). On reply failure (`Unknown message`), fall back to channel send.
- Empty `!gem` → `どしたん?話きこか?`
- Safety settings: all major harm categories set to `BLOCK_NONE`.
- Generation: temperature 1, top_p 0.95, top_k 40, max_output_tokens 8192.
- API calls run in a thread executor with up to 3 retries.

**Prompt management** (Parent in guild; in DMs no role check)

| Command | Behavior |
|---------|----------|
| `!show_prompt` | Show current initial prompt |
| `!set_prompt <text>` | Replace in-memory initial prompt |
| `!reset_prompt` | Restore env default and **recreate** chat session |

Natural-language prompt helpers exist in `_try_natural_language_command` but are **not wired** into `on_message` — treat as incomplete unless connected.

### 6.4 Infant engagement

**Manual (Parent)**

- `!check_infant` — random Infant, friendly check-in message.
- `!discuss_topic` — from recent channel messages, ask a random Infant about a topic.

**Periodic (Parent-controlled)**

- Loop default: every **30 minutes**; configurable **10–1440** minutes.
- Skips JST **00:00–06:00**.
- Picks random text channel under baby-room category + random Infant; uses last ~5 user messages (or general topics if empty); posts `@infant` + LLM short message (≤100 chars, 1–2 emoji, time-aware greeting).
- Commands: `!start_periodic_check`, `!stop_periodic_check`, `!set_check_interval`, `!check_status`.

### 6.5 Channel / permission admin (Parent)

| Command | Requirement |
|---------|-------------|
| `!list_categories` | List categories + IDs |
| `!list_channels [category_id]` | Channels + permission sync status |
| `!sync_permissions [category_id] [channel_id]` | Sync to category; default category = baby room |
| `!sync_all_permissions` | Sync all channels under all categories |

### 6.6 Message purge (Parent)

- `!purge_user <mention|id|name> [limit]`
- Guild only; confirmation via ✅/❌ (30s timeout).
- Scans text channels, threads, and voice channels; requires bot `manage_messages`.
- `limit <= 0` → effectively unlimited; rate-limit aware deletes; bulk for messages < 14 days.

### 6.7 Help

- `!help_command` — lists commands filtered by Parent / Toddler / everyone.

### 6.8 Slash / owner commands (`RoleOperation`)

| Command | Access | Behavior |
|---------|--------|----------|
| `/getallmessages` | Administrator | Fetch DB messages (needs working DB) |
| `/shutdown` | Administrator | Log and close bot |
| `!sync` | Bot owner | Sync app command tree (`~` `*` `^` guild variants) |

---

## 7. Data layer (scaffold — inactive)

**Requirement today:** bot must run **without** a database. `settings.get_db_url()` returns `None`; `migrate_tables()` is commented out in `main.py`.

Scaffold intent (for future work):

- Table `message`: `pk`, `member_id`, `channel_id`, `msg_id`, timestamps, optional `embedding Vector(1536)`.
- Commands `!save_message` / `!get_messages` and `/getallmessages` assume a live async session — they will fail until DB URL and migrate are restored.

Do not re-enable DB paths without restoring `get_db_url()`, env vars, and an explicit migrate step.

---

## 8. Cross-cutting requirements

1. **Language:** User-facing bot replies are primarily **Japanese**; code/comments mix EN/JA.
2. **Single guild:** Assume `bot.guilds[0]` / `GUILD_ID` for server-scoped features.
3. **Roles are name-based** (`"Parent"`, `"Toddler"`, `"Infant"`) — renaming roles in Discord breaks authz.
4. **Logging:** INFO to stdout via `Logger('discord')` / `'database'`.
5. **Secrets:** Never commit `.env`; never log API keys or tokens.
6. **Long Discord messages:** Split near 2000 characters when sending large outputs.
7. **Errors:** Prefer Japanese user-visible error replies; log stack/details server-side.

---

## 9. How to run

```bash
# 1. Create .env with all required Settings fields
# 2. Install
pip install -r requirements.txt
# 3. Run
python main.py
```

Docker:

```bash
docker build -t discord-bot-with-llm .
docker run --env-file .env discord-bot-with-llm
```

Bot needs Discord permissions consistent with features: send messages, manage roles, manage messages (purge), read history, add reactions, embed links, etc.

---

## 10. Extending the bot (conventions for humans & LLMs)

1. **New Discord feature** → add to the appropriate cog (`Gemini` = AI/engagement/tools; `RoleOperation` = membership/reactions/slash lifecycle). Avoid bloating `main.py`.
2. **New config** → add to `Config.Settings` and document in §5 of this file.
3. **New role-gated command** → declare with `@commands.has_role` / `has_any_role` and update `!help_command` maps.
4. **Do not** add exploit-style automation, scrape secrets, or expand purge beyond Parent-confirmed flows.
5. **Update this file** whenever behavior, env vars, roles, or structure change — this is the requirements contract.

---

## 11. Known gaps / tech debt (as of last review)

Documented so agents do not “rediscover” them as mysteries:

| Item | Notes |
|------|-------|
| DB disabled | `get_db_url()` → `None`; migrate commented out |
| `OPENAI_API_KEY` unused | Legacy / future |
| Hardcoded channel/category IDs | Prefer env |
| `_try_natural_language_command` | Implemented, not called from message flow |
| `set_prompt` | Updates memory; may not restart chat until `reset_prompt` |
| Reaction embed description ternary | Always truthy string expression — content always used |
| `fastapi` in requirements | Not used by current entrypoint |
| Periodic check / infant features | Depend on Infant role + baby-room category existing |

---

## 12. Quick command cheat sheet

**Anyone:** `!help_command`

**Parent / Toddler:** `!gem`, `!運勢` / `!fortune`, `!save_message`, `!get_messages`, `!set_history_limit`

**Parent:** periodic check controls, channel/permission sync, `!check_infant`, `!discuss_topic`, `!purge_user`, prompt show/set/reset (guild)

**Mention:** `@bot <message>` → Gemini reply with channel history context

**Fortune:** `!運勢` / `!fortune` → Jev decision + Discord embed (see §13)

---

## 13. Feature — 運勢占い (Jev) 【実装済み・推奨パターン】

> Status: **implemented**. Set `TYPESAFE_API_KEY` on Koyeb (and optionally local `.env`).
> Do not reopen product choices below unless this section is explicitly revised.

### 13.1 Product decisions (frozen)

| Topic | Decision |
|-------|----------|
| Trigger | Prefix only: `!運勢` and `!fortune` (aliases). **Not** every `@bot` mention. |
| Existing Gemini chat | Unchanged (`@bot` / `!gem` stay free-form chat). |
| Who can run | `Parent` or `Toddler` (same as `!gem`). Infants: friendly deny or ignore. |
| Message sample | **Current channel only.** Last **10** messages by the invoking author (exclude bots, empty content). Oldest→newest in `state`. |
| If fewer than 10 | Use whatever exists (min 1). If **0** usable messages → reply that there is not enough speech history; do not call Jev. |
| Decision engine | **TypeSafe Jev** (`jev-latest`) via `POST https://api.typesafe.ai/v1/systemone` or `typesafe-sdk`. |
| Schema style | Jev typed `questions` (Choice / Score / Noul). Not free-form LLM JSON. |
| “Highest probability” | For each `Choice`, take API `.choice` (argmax). Optionally show top probability % in the embed footer/field. |
| User-facing copy | **Template / Discord Embed only** for v1 (no Gemini prose pass). Fast, cheap, no second-model dependency for this feature. |
| Hosting | Deploy via existing **GitHub → Koyeb** pipeline after merge to `main`. |

### 13.2 Jev fortune schema (v1)

Single request, shared `state`, parallel questions:

| Key | Type | Criteria / levels |
|-----|------|-------------------|
| `overall` | Choice | `大吉`, `中吉`, `小吉`, `吉`, `末吉`, `凶`, `大凶` |
| `love` | Choice | `絶好調`, `順調`, `普通`, `注意`, `低調` |
| `work` | Choice | same as love |
| `money` | Choice | same as love |
| `health` | Choice | same as love |
| `mood` | Score | 1–5（今日の気分の乗りやすさ） |
| `caution` | Noul | 「今日は慎重に動いた方がよいか」 |
| `advice` | Choice | Fixed Japanese advice idioms (≤8 options), e.g. 深呼吸してから動く / 連絡を大切に / 新しいことに触れる / 休息を優先 / 小さな整理をする / 笑うことを意識 / 早寝を心がける / 水を多めに |

Instructions (per question) should tell Jev to infer from the author’s recent messages in `state`, not from calendar astrology alone.

### 13.3 `state` payload shape

Prefer a structured string (or SDK object) including:

- `display_name`, `discord_user_id`
- `channel_name` / `channel_id`
- `messages`: numbered list of the 10 texts (and optional timestamps)
- Optional one-line: current mention/command text if any args after `!運勢`

Do **not** put secrets or other users’ private channel content into `state`.

### 13.4 Discord UX

1. User runs `!運勢` in a text channel.
2. Bot shows typing, fetches history, calls Jev.
3. Reply with an **Embed**:
   - Title: `{display_name} さんの今日の運勢`
   - Fields: 総合 / 恋愛 / 仕事 / 金運 / 健康 / 気分(Score) / アドバイス
   - Footer: e.g. `総合の確信度: {confidence:.0%}` or top-choice probability
   - If `caution.noul` ≥ 0.6, add a short warning line in description
4. Errors (Japanese, no raw vendor payload):
   - Missing/invalid `TYPESAFE_API_KEY` → 「運勢APIのキーが未設定か無効です。Koyebの環境変数を確認してください。」
   - Timeout / upstream → 「占いに失敗しました。しばらくして再試行してください。」
   - Log full error server-side only.

### 13.5 Code layout (implementation map)

| Piece | Where |
|-------|--------|
| Env | `Config.Settings.TYPESAFE_API_KEY: str` (required once feature ships; or optional with runtime check) |
| Schema constants | New `src/FortuneSchema.py` (questions factory + embed formatter) |
| Jev client wrapper | New `src/JevClient.py` (async-friendly: run sync SDK in executor) |
| Command | Prefer small cog `src/Cogs/Fortune.py` **or** methods on `Gemini` cog — **prefer new cog** to keep chat vs fortune separated |
| Wire-up | `DiscordBot.setup_hook` → `add_cog(Fortune(...))` |
| Deps | `typesafe-sdk` in `requirements.txt` |
| Docs | This section + `!help_command` entry |
| Secrets | Set on **Koyeb** env after key is ready; never commit |

### 13.6 Implementation status

Shipped modules: `src/FortuneSchema.py`, `src/JevClient.py`, `src/Cogs/Fortune.py` (registered in `DiscordBot.setup_hook`). Dependency: `typesafe-sdk`.

### 13.7 Non-goals (v1)

- Replacing `@bot` Gemini chat with fortune
- Guild-wide message scan
- Birthday / 星座 / 八字 calendars
- Persisting fortune results to DB
- Gemini post-processing of fortune prose
- Natural-language “占って” without prefix (can be v2)

### 13.8 Open only for later (not blocking v1)

- Show full probability bars per Choice
- Daily cache per user (one fortune / UTC+9 day)
- Infant-allowed lightweight variant
