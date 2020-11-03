import discord
from discord.ext import commands

import src.async_database as ad

class GroupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_int(self, what):
        try:
            int(what)
            return True
        except ValueError:
            return False

    def get_message(self, fetch):
        msg = ""
        for item in fetch:
            msg = msg + f"Para se inscrever no grupo {item['group_name']}, reaja com {item['react_emoji']}\n"
        return msg

    async def show_message(self, conn, ctx, guild_did):
        guild_conf = await conn.fetchrow("SELECT channel_id, message_id FROM guild_conf WHERE guild_did = $1", guild_did)
        if not guild_conf:
            await ctx.send("**Atenção**: É necessário executar o comando setup.")
            return

        channel = ctx.guild.get_channel(guild_conf['channel_id'])
        sent_message = await channel.fetch_message(guild_conf['message_id'])

        fetch = await conn.fetch("SELECT group_name, react_emoji FROM groups WHERE guild_did = $1", guild_did)

        await sent_message.edit(content=self.get_message(fetch))

        for item in fetch:
            await sent_message.add_reaction(emoji=item['react_emoji'])

    @commands.command(pass_context=True)
    async def create(self, ctx, *, group_name):
        conn = await ad.connect_db()
        guild_did = await ad.create_get_guild_record(conn, ctx.guild.id)
        role_id = await conn.fetchval("SELECT role_id FROM groups WHERE guild_did = $1 AND group_name = $2", guild_did, group_name)
        category_id = await conn.fetchval("SELECT category_id FROM guild_conf WHERE guild_did = $1", guild_did)
        if not category_id:
            await ctx.send("O servidor ainda não foi configurado. Execute o comando setup.")
            await conn.close()
            return

        if not role_id:
            await ctx.send("Desculpe, o grupo não foi encontrado.")
            await conn.close()
            return

        await ctx.send("Qual o tipo de canal? (1) Público (2) Privado (3) Protegido")
        response = await self.bot.wait_for('message', timeout=45, check=lambda message: message.author == ctx.author and self.is_int(message.content))

        choice = int(response.content)
        role = ctx.guild.get_role(role_id)

        overwrites = {
            role: discord.PermissionOverwrite(send_messages=True, read_messages=True)
        }

        if choice == 1:
            pass
        elif choice == 2:
            overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(read_messages=False)
        elif choice == 3:
            overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(send_messages=False)
        else:
            pass

        category = ctx.guild.get_channel(category_id)
        channel = await ctx.guild.create_text_channel(group_name.replace(" ", "-"), overwrites=overwrites, category=category)
        await conn.close()

    @commands.command(pass_context=True)
    async def new(self, ctx, emoji, *, group_name):
        conn = await ad.connect_db()
        guild_did = await ad.create_get_guild_record(conn, ctx.guild.id)
        group_id = await conn.fetchval("SELECT id FROM groups WHERE guild_did = $1 AND group_name = $2", guild_did, group_name)
        if group_id:
            await ctx.send("Já existe um grupo com este nome.")
            await conn.close()
            return

        group_role = await ctx.guild.create_role(name=group_name,
                                                 colour=discord.Colour.blurple(),
                                                 mentionable=True, hoist=False)
        await conn.execute('''INSERT INTO groups (guild_did, group_name, role_id, react_emoji)
                              VALUES ($1, $2, $3, $4)''', guild_did, group_name, group_role.id, emoji)
        await self.show_message(conn, ctx, guild_did)
        await conn.close()

    @commands.is_owner()
    @commands.command(pass_context=True)
    async def setup(self, ctx):
        conn = await ad.connect_db()
        guild_did = await ad.create_get_guild_record(conn, ctx.guild.id)

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(send_messages=True)
        }

        category = await ctx.guild.create_category("grupos", overwrites=overwrites)
        channel = await ctx.guild.create_text_channel("entrar", category=category)
        fetch = await conn.fetch("SELECT group_name, react_emoji FROM groups WHERE guild_did = $1", guild_did)
        sent_msg = await channel.send(self.get_message(fetch))
        for item in fetch:
            await sent_msg.add_reaction(emoji=item['react_emoji'])

        await conn.execute('''INSERT INTO guild_conf (guild_did, category_id, channel_id, message_id)
                              VALUES
                              ($1, $2, $3, $4)''', guild_did, category.id, channel.id, sent_msg.id)
        await conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return

        conn = await ad.connect_db()
        guild_did = await conn.fetchval("SELECT id FROM guilds WHERE guild_id = $1", payload.guild_id)
        if not guild_did:
            await conn.close()
            return

        message_id = await conn.fetchval("SELECT message_id FROM guild_conf WHERE guild_did = $1", guild_did)
        if not message_id or payload.message_id != message_id:
            await conn.close()
            return

        groups = await conn.fetch("SELECT role_id, react_emoji FROM groups WHERE guild_did = $1", guild_did)
        for group in groups:
            if str(payload.emoji) == group['react_emoji']:
                guild = self.bot.get_guild(payload.guild_id)
                user = guild.get_member(payload.user_id)
                await user.add_roles(guild.get_role(group['role_id']))
                break
        await conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return

        conn = await ad.connect_db()
        guild_did = await conn.fetchval("SELECT id FROM guilds WHERE guild_id = $1", payload.guild_id)
        if not guild_did:
            await conn.close()
            return

        message_id = await conn.fetchval("SELECT message_id FROM guild_conf WHERE guild_did = $1", guild_did)
        if not message_id or payload.message_id != message_id:
            await conn.close()
            return

        groups = await conn.fetch("SELECT role_id, react_emoji FROM groups WHERE guild_did = $1", guild_did)

        for group in groups:
            if str(payload.emoji) == group['react_emoji']:
                guild = self.bot.get_guild(payload.guild_id)
                user = guild.get_member(payload.user_id)
                role = guild.get_role(group['role_id'])
                try:
                    await user.remove_roles(role)
                except discord.HTTPException:
                    pass

        await conn.close()
