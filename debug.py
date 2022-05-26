from replit import db


#print(db["guilds"])
#db["guilds"]["678996875202002944"]["active_question"] = False



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

print(get_leaderboard("678996875202002944"))