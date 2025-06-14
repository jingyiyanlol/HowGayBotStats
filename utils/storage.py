import sqlite3
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# Use SQLite connection with thread safety disabled (same as before)
conn = sqlite3.connect("gayness.db", check_same_thread=False)
cur = conn.cursor()

# Stats table with composite primary key (chat_id + user_id + timestamp truncated to minute)
cur.execute("""
CREATE TABLE IF NOT EXISTS stats (
    chat_id TEXT,
    user_id TEXT,
    percentage INTEGER,
    timestamp DATETIME,
    PRIMARY KEY (chat_id, user_id, timestamp),
    UNIQUE(chat_id, user_id, timestamp)
)
""")

# Table to store user information
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    name TEXT
);
""")

# Store last update timestamp for each chat
cur.execute("""
CREATE TABLE IF NOT EXISTS last_update (
    chat_id TEXT PRIMARY KEY,
    last_timestamp TEXT
)
""")
conn.commit()

def log_stat(chat_id, user_id, username, name, percent, ts):
    try:
        # Insert stat
        cur.execute("""
            INSERT INTO stats (chat_id, user_id, percentage, timestamp)
            VALUES (?, ?, ?, ?)
        """, (chat_id, user_id, percent, ts.isoformat()))
        conn.commit()

        # Upsert user info
        existing = cur.execute("SELECT username, name FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            existing_username, existing_name = existing
            # Update only if we have new info
            if username and username != existing_username:
                cur.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            if name and name != existing_name:
                cur.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        else:
            # Insert if not exists
            cur.execute("""
                INSERT INTO users (user_id, username, name)
                VALUES (?, ?, ?)
            """, (user_id, username or "unknown", name or ""))
        conn.commit()

        logger.info(f"Logged stat: chat_id={chat_id}, user_id={user_id}, {percent}% at {ts}")
    except sqlite3.IntegrityError:
        logger.info(f"Duplicate skipped: user_id={user_id} in chat_id={chat_id} at {ts}")


INDIVIDUAL_STATS_LABELS = {
        100: "💯 100% GAY 👨‍❤️‍💋‍👨",
        88:  "🐉 88% Huat Gay 🍀",
        69:  "☯️ 69% Gay 👯",
        0:   "🙅‍♂️ 0% Gay 🚫"
    }

def get_user_stats_all(chat_id, user_id):
    cur.execute("""
        SELECT percentage, COUNT(*)
        FROM stats 
        WHERE chat_id = ? AND user_id = ?
        GROUP BY percentage
        ORDER BY percentage DESC
    """, (chat_id, user_id))
    results = cur.fetchall()
    if not results:
        return "No stats yet!"
    
    return "\n".join([f"{p}% Gay: {c} X" for p, c in results])

def get_user_stats_nice(chat_id, user_id):
    cur.execute("""
        SELECT percentage, COUNT(*), MAX(timestamp)
        FROM stats 
        WHERE chat_id = ? AND user_id = ? AND percentage IN (0, 69, 88, 100)
        GROUP BY percentage
        ORDER BY percentage DESC
    """, (chat_id, user_id))
    results = cur.fetchall()
    if not results:
        return "No nice stats yet!"

    output = []
    for target_percent in [100, 88, 69, 0]:
        for percent, count, last_time in results:
            if percent == target_percent:
                formatted_time = last_time.split("T")[0] + " " + last_time.split("T")[1][:5]  # YYYY-MM-DD HH:MM
                output.append(
                    f"{INDIVIDUAL_STATS_LABELS[percent]}\n→ {count} times (last on {formatted_time})"
                )
                break

    return "\n\n".join(output)


def get_leaderboard(chat_id):
    cur.execute("""
        SELECT s.percentage, u.username, u.name, COUNT(*) as cnt
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.chat_id = ?
        GROUP BY s.percentage, u.username, u.name
    """, (chat_id,))
    rows = cur.fetchall()

    if not rows:
        return "No leaderboard yet! Use @HowGayBot to start contributing your stats."

    # Only keep specific % categories
    wanted_percents = {
        100: "💯The Great Gays 👨‍❤️‍💋‍👨100%",
        88: "🐉 88% Huat Gays 🍀",
        69: "☯️ 69 Gays 👯",
        0:  "🙅‍♂️ 0% Gays 🚫",
    }

    leaderboard = {key: [] for key in wanted_percents}

    for percent, username, name, cnt in rows:
        if percent not in wanted_percents:
            continue

        display = f"@{username}" if username and username != "unknown" else name or "unknown"
        leaderboard[percent].append(f"{display} X {cnt}")

    # Compose output
    output = []
    for percent in [100, 88, 69, 0]:  # Maintain order
        entries = leaderboard[percent]
        if entries:
            output.append(f"{wanted_percents[percent]}")
            output.extend(entries)

    if not output:
        return "No leaderboard yet! Use @HowGayBot to start contributing your stats."

    return "\n".join(output)



def get_last_update(chat_id):
    cur.execute("SELECT last_timestamp FROM last_update WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    return datetime.fromisoformat(row[0]) if row else datetime.min

def update_last_timestamp(chat_id, ts):
    cur.execute("REPLACE INTO last_update (chat_id, last_timestamp) VALUES (?, ?)", (chat_id, ts.isoformat()))
    conn.commit()

def delete_chat_data(chat_id):
    logger.info(f"Bot removed from chat {chat_id}, data deleted")
    cur.execute("DELETE FROM stats WHERE chat_id=?", (chat_id,))
    cur.execute("DELETE FROM last_update WHERE chat_id=?", (chat_id,))
    conn.commit()

def get_chat_stats_all():
    cur.execute("""
        SELECT *
        FROM stats """)
    results = cur.fetchall()
    if not results:
        return "No stats yet!"
    return "\n".join([f"Chat: {chat_id}, User: {user_id}, Percentage: {percentage}, Timestamp: {timestamp}" for chat_id, user_id, percentage, timestamp in results])

def get_users_all():
    cur.execute("SELECT user_id, username, name FROM users")
    results = cur.fetchall()
    if not results:
        return "No users found!"
    return "\n".join([f"User ID: {user_id}, Username: {username}, Name: {name}" for user_id, username, name in results])