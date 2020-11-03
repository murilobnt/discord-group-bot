import discord
from discord.ext import commands

import os
from src.group_cog import GroupCog

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='g!', intents=intents)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.add_cog(GroupCog(bot))
bot.run(os.environ['DISCORD_GROUP_BOT_KEY'])
