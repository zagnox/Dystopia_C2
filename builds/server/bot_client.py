import discord

intents = discord.Intents.all()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)