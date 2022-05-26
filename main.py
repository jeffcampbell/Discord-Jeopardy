import asyncio
from datetime import datetime
from dateutil import parser
import discord
from fuzzywuzzy import fuzz
import logging
from mediawiki import MediaWiki
import re
import os
from replit import db
import requests
from unidecode import unidecode

logging.basicConfig(filename='console.log', level=logging.INFO)
client = discord.Client()
wikipedia = MediaWiki()
discord_token = os.environ['discord_bot_token']

class Jeopardy:
    async def get_question(guild, message, channel):
      if str(guild.id) not in db["guilds"]:
        Bot.setup(guild,message.author)
      gld = db["guilds"][str(guild.id)]
      if gld["active_question"] is True:
        embed=discord.Embed(title="Category: {}".format(gld["question"]["category"]["title"]), description="For ${}, {}".format(gld["question"]["value"],gld["question"]["question"]))
        await channel.send(embed=embed)
    
      elif gld["active_question"] is False:    
        jservice = "https://jservice.io/api/random"
        score = None
        while not score:
            question = requests.get(jservice).json()
            score = question[0]["value"]
            if not score:
                logging.info("Question with no score, tossing out.")
                continue
        gld["question"] = question[0]
        gld["question"]["answer"] = re.sub(r"\<[^>]*>", '', question[0]["answer"], flags=re.IGNORECASE)
        gld["wikipedia"] = gld["question"]["answer"]
        print(gld["wikipedia"])
        gld["active_question"] = True
        dp = parser.parse(gld["question"]["airdate"][:-1])
        d = datetime.strftime(dp, "%B %d %Y")
    
        embed=discord.Embed(title="Category: {}".format(gld["question"]["category"]["title"]), description="For ${}, {}".format(gld["question"]["value"],gld["question"]["question"]))
        embed.set_footer(text="Airdate: {}".format(d))
        await channel.send(embed=embed)
        client.loop.create_task(Timers.question_timer(str(guild.id),channel,gld["question"]["id"]))
      else:
        await channel.send("Could not find question. Perhaps something is wrong?")
    
    async def check_answer(guild, message, channel, player):
        if str(guild) not in db["guilds"]:
          Bot.setup(guild,message.author)
        gld = db["guilds"][str(guild)]
        if gld["active_question"] == False:
            logging.info("No active question")    
        else:
            logging.info("Found active question")
            message = re.sub(r"^(what|whats|where|wheres|who|whos)(\s)(is|are)", '', message, flags=re.IGNORECASE)
            logging.info("Answer pre-decoding: {}".format(gld["question"]))
            decoded = unidecode(gld["question"]["answer"])
            logging.info("Answer post-decoding: {}".format(decoded))
            check = fuzz.ratio(message,decoded)
            score = gld["question"]["value"]
            if gld["question"]["id"] == db["players"][player.display_name]["last_question"]:
                await channel.send("You have already tried to answer this question, {}!".format(player.display_name))
    
            elif check > 60:
                Bot.update_score(guild, player, score, gld["question"]["id"])
                await channel.send("That is correct, {}! Your score is now ${}.".format(player.display_name,db["players"][player.display_name]["score"]))
                del gld["question"]
                gld["active_question"] = False
            else:
                score = score * -1
                Bot.update_score(guild, player, score, gld["question"]["id"])
                await channel.send("That is incorrect, {}! Your score is now ${}.".format(player.display_name,db["players"][player.display_name]["score"]))
    
class Bot:
    def setup(guild,player):
      print("Starting setup...")
      ### New Guild Setup ###
      gcheck = db.prefix("guilds")
      pcheck = db.prefix("players")
      if not gcheck:
        db["guilds"] = {}
      if not pcheck:
        db["players"] = {}
      print(guild)
      guild_id = str(guild)
      if guild_id not in db["guilds"]:
        print("Creating Guild... ")
        db["guilds"][guild_id] = {}
        db["guilds"][guild_id]["active_question"] = False
      if player.display_name not in db["players"]:
        print("Creating Player... " + player.display_name)
        db["players"][player.display_name] = {}
        db["players"][player.display_name]["guild"] = guild_id
        db["players"][player.display_name]["score"] = 0
        db["players"][player.display_name]["last_question"] = 0
    
    def admin_tools(guild,user,channel,action):
      #Not working
      if not user.guild_permissions.administrator:
        update = "Sorry, only admin can reset the Jeopardy score.\nUse ❓ to request a question.\nUse 🏅 to check the leaderboard."
      else:
        if action == "reset":
    #db call reset scores
            update = "Scores have been reset!\nUse ❓ to request a question."
    
      return update
    
    def get_leaderboard(guild):
      #Not working
      for player in db["players"]:
        leaders = {}
        if db["players"][player]["guild"] == str(guild):
          leader = {player: {'name': player, 'score': db["players"][player]["score"]}}
          leaders.update(leader)
        leaderboard = "Let's take a look at the leaderboard:\n"
        place = 0
        medals = ["🥇","🥈","🥉"]
        for leader in leaders.values():
            leaderboard = leaderboard + "{} {} with a score of ${}\n".format(medals[place],leader["name"],leader["score"])
            place = place + 1

      return leaderboard
    
    def update_score(guild, player, score, question):
      logging.info("Checking for user...")
    
      if not db["players"][player.display_name]:
        logging.info("No user found, adding...")
        Bot.setup(guild,player)
      else:
        logging.info("User found, updating score...")
        db["players"][player.display_name]["score"] = score + db["players"][player.display_name]["score"]
        db["players"][player.display_name]["last_question"] = question
      logging.info("Done.")
    
      return score
    
class Wiki:
    async def get_wiki(guild, message):
      gld = db["guilds"][str(guild)]
      logging.info("Found a question for wikipedia")
      try:
        search = wikipedia.search(gld["wikipedia"])
        page = wikipedia.page(search[0])
        summary = page.summarize(sentences=2)
      except Exception as e:
        logging.warning("Potential disambiguation: {}".format(e))
        summary = "Too many results! https://en.wikipedia.org/w/index.php?search={}".format(gld["wikipedia"])

      embed=discord.Embed(title="{}".format(gld["wikipedia"]), description=summary)
      await message.channel.send(embed=embed)

class Timers:
    async def question_timer(guild, channel, question_id):
      print("Starting timer for {}...".format(question_id))
      await asyncio.sleep(30)
      print("Time is up for question {}".format(question_id))
      if db["guilds"][guild]["active_question"] == False or db["guilds"][guild]["question"]["id"] != question_id:
        print("Question was answered")
      else:
        await channel.send("Time is up! The answer is {}".format(db["guilds"][guild]["question"]["answer"]))
    
        msg = await client.get_channel(channel.id).history(limit=1).flatten()
        msg = msg[0]
        await msg.add_reaction("🔎")
        db["guilds"][guild]["active_question"] = False
        del db["guilds"][guild]["question"]

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):

  channel = message.channel
  question_format = re.match("^(what|whats|where|wheres|who|whos)(\s)",message.content,re.IGNORECASE)

  if message.author == client.user:
    return

  if message.content.startswith('!jeopardy'):
    if message.author.guild_permissions.administrator:
        result = "Use ❓ to request a question.\nUse 🏅 to check the leaderboard.\nUse ❌ to reset everyone's score (admin only)" 
    else:
        result = "Use ❓ to request a question.\nUse 🏅 to check the leaderboard." 

    await channel.send(result)

  if message.content.startswith('❓'):
    await Jeopardy.get_question(message.guild,message,channel)

  if message.content.startswith('🏅'):
    result = Bot.get_leaderboard(message.guild.id,channel)

    await channel.send(result)

  if message.content.startswith('❌'):
    action = "reset"
    result = Bot.admin_tools(message.guild.id,message.author,channel,action)
    if result:
      await channel.send(result)

  if question_format:
    logging.info("found an answer!")
    await Jeopardy.check_answer(message.guild.id,message.content,channel,message.author)

@client.event
async def on_reaction_add(reaction, user):
  guild = reaction.message.guild.id
  message = reaction.message

  if (reaction.emoji == "🔎"):
    if user != client.user:
      await Wiki.get_wiki(guild,message)

client.run(discord_token)