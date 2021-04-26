import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import discord
import pandas as pd
import requests
from discord.ext import commands

from secret import DISCORD_TOKEN, LEADERBOARD_CHANNEL_ID, MESSAGE_CHANNEL_ID

bot = commands.Bot(command_prefix='/')

@bot.command()
async def qual(ctx, *args):

    isDebug = False

    league = args[0]
    if len(args) == 2 and args[1] == 'debug':
        isDebug = True

    if isDebug:
        await ctx.send("得点を解析するビ！（デバッグモード）")
    else:
        channel = bot.get_channel(MESSAGE_CHANNEL_ID)
        await channel.send("得点を解析するビ！")

    players_data = pd.read_csv(
        f'{league}_userdata.csv', index_col=0, dtype=object)
    songs_data = pd.read_csv(f'{league}_songdata.csv')

    scarping_range = 5
    if isDebug:
        scarping_range = 2

    songs_id = list(songs_data['id'])
    songs_id = list(map(str, songs_id))

    def local(data, name, song_idx):
        num_data = data.iloc[:, 1:].astype('float64')
        data_s = num_data.sort_values(song_idx, ascending=False)
        return data_s.index.get_loc(name)+1

    for player in players_data.iterrows():
        personal_data = player[1]
        name = personal_data.name
        url = personal_data['url']
        print(f'{name} searching')
        for page in range(1, scarping_range+1):
            page_url = f'{url}&page={page}&sort=2'
            source = requests.get(page_url).text
            pattern = r'<a href="/leaderboard/(.*?)">'
            leaderboard_ids = re.findall(pattern, source)
            pattern = r'<span class="songTop pp">(.*?)<span style="color:(.*?);">(.*?)</span>(.*?)</span> <span class="songTop mapper">(.*?)</span>'
            song_informations = re.findall(pattern, source)
            pattern = r'<span class="scoreBottom">(.*?)</span>'
            original_scores = re.findall(pattern, source)
            sub1 = len(leaderboard_ids) == len(song_informations)
            sub2 = len(song_informations) == len(original_scores)
            sub3 = sub1 and sub2
            if not sub3:
                await ctx.send('スクレイピングにミスがあるようなので一旦飛ばします。すまんな。')
                continue
            for lead, orig, info in zip(leaderboard_ids, original_scores, song_informations):
                print(lead, info)
                if lead not in songs_id:
                    continue
                idx = songs_id.index(lead)
                notes = songs_data.iloc[idx]['notes']
                if 'score' in orig:
                    score = int(orig[7:-3].replace(',', ''))
                    acc = score/(115*8*int(notes)-7245)*100
                    acc = Decimal(str(acc)).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP)
                    acc = float(acc)
                else:
                    acc = float(orig[-6:-1])
                song_idx = f'song{idx}'
                if acc > float(players_data.at[name, song_idx]):
                    players_data.at[name, song_idx] = acc
                    local_rank = local(players_data, name, song_idx)
                    text = f'{name}さんが {info[0]} {info[2]} を更新！ acc ... {acc} (譜面内順位 **#{local_rank}**)'
                    print(text)
                    if isDebug:
                        await ctx.send(text)
                    else:
                        channel = bot.get_channel(MESSAGE_CHANNEL_ID)
                        await channel.send(text)

    num_data = players_data.iloc[:, 1:].astype('float64')
    total = num_data.sum(axis=1)
    total_s = total.sort_values(ascending=False)

    text = f':crown: 現在の {league} 総合ランキング:lizard:\n'
    text += f'... at {datetime.now()}\n\n'
    count = 0
    for t in total_s.index.values:
        count += 1
        score = total_s[t]
        score = int(score*100)
        score = float(score)/100
        if "棄権" in t:
            count -= 1
            text += f'--- : {score:6.2f} pt ... {t}\n'
        else:
            text += f'#{count:2} : {score:6.2f} pt ... **{t}**\n'
            count_limit = 8
            if league == 'j1':
                count_limit = 7
            if count == count_limit:
                text += '🧱🧱🧱🧱🧱🧱 本選進出の壁 🧱🧱🧱🧱🧱🧱\n'

    song_list = list(songs_data['name'])
    diff_list = list(songs_data['diff'])
    for i, (song, diff) in enumerate(zip(song_list, diff_list)):
        text += f'\n**{song} {diff}**  の譜面内ランキング\n'
        data_s = num_data.sort_values(f'song{i}', ascending=False)
        data_s = data_s[f'song{i}']
        for j in range(5):
            add_text = f'#{j+1:2} : {data_s[j]:5.2f} % ... {data_s.index.values[j]}\n'
            text += add_text

    print(text)

    if isDebug:
        await ctx.send(text)
    else:
        try:
            channel = bot.get_channel(LEADERBOARD_CHANNEL_ID[league])
            lid = channel.last_message_id
            last_message = await channel.fetch_message(lid)
            await last_message.edit(content=text)
        except:
            channel = bot.get_channel(LEADERBOARD_CHANNEL_ID[league])
            await channel.send(text)

    if isDebug:
        await ctx.send("解析終了しました")
    else:
        channel = bot.get_channel(MESSAGE_CHANNEL_ID)
        await channel.send("解析終了しました")
        players_data.to_csv(f'{league}_userdata.csv')

    print("done")

print("bot running...")
bot.run(DISCORD_TOKEN)
