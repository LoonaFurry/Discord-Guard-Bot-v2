import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import discord
from discord.ext import commands
import asyncio

# Initialize tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")
model = AutoModelForSequenceClassification.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")

# Perform sentiment analysis on text
def perform_sentiment_analysis(text):
    inputs = tokenizer.encode_plus(
        text,
        add_special_tokens=True,
        return_tensors="pt"
    )
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=1)
    return predictions.item()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    sentiment = perform_sentiment_analysis(message.content)

    if sentiment == 0:
        await message.delete()
        warning_message = await message.channel.send(f'{message.author.mention}, please refrain from using inappropriate language.')
        await asyncio.sleep(10)
        await warning_message.delete()

    await bot.process_commands(message)

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot.run('your-discord-token-here')
