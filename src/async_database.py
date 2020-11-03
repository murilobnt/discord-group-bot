import asyncpg
import asyncio
import os

async def connect_db():
    DATABASE_URL = os.environ['DATABASE_URL']
    dsn = '?sslmode=require'
    conn = await asyncpg.connect(DATABASE_URL + dsn)
    return conn

async def create_get_user_record(conn, user_id):
    user_fetch = await conn.fetchval("SELECT id FROM users WHERE user_id = $1", user_id)
    if user_fetch is None:
        user_fetch = await conn.fetchval('''INSERT INTO users (user_id) VALUES ($1) RETURNING id''', user_id)
    return user_fetch

async def create_get_guild_record(conn, guild_id):
    guild_fetch = await conn.fetchval("SELECT id FROM guilds WHERE guild_id = $1", guild_id)
    if guild_fetch is None:
        guild_fetch = await conn.fetchval('''INSERT INTO guilds (guild_id) VALUES ($1) RETURNING id''', guild_id)
    return guild_fetch

# async def create_get_user_guild_id(conn, user_id, guild_id):
#     user_fetch = await create_get_user_record(conn, user_id)
#     guild_fetch = await create_get_guild_record(conn, guild_id)
#     user_guild_fetch = await conn.fetchval("""SELECT id FROM user_guild WHERE user_did = $1 AND guild_did = $2""", user_fetch, guild_fetch)
#     if user_guild_fetch is None:
#         user_guild_fetch = await conn.fetchval('''INSERT INTO user_guild (user_did, guild_did) VALUES ($1, $2) RETURNING id''', user_fetch, guild_fetch)
#     return user_guild_fetch
