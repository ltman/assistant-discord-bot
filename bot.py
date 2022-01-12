import discord
from discord import channel
from discord.ext import commands
from discord.utils import valid_icon_size
from gtts import gTTS
from pydub import AudioSegment
import youtube_dl
import os, random
import asyncio
import urllib.request
import uuid

from functions.join import __join
from functions.leave import __leave

async def sync_to_async(fn):
    loop = asyncio.get_event_loop()
    result  = await loop.run_in_executor(None, fn)
    return result

client = commands.Bot(command_prefix="-")

BOT_TOKEN='' # Insert Discord Bot Token Here
# If you wish to securely hide your token, you can do so in a .env file.
# 1. Create a .env in the same directory as your Python scripts
# 2. In the .env file format your variables like this: VARIABLE_NAME=your_token_here
# 3. At the top of the Python script, import os
# 4. In Python, you can read a .env file using this syntax:
# token = os.getenv(VARIABLE_NAME)

global player_queue
player_queue = {}

global player_current
player_current = {}

def delete_song_there(filename):
    if filename.find('/effects') >= 0 or filename.find('/chokde'): return
    song_there = os.path.isfile(filename)
    try:
        if song_there:
            os.remove(filename)
    except Exception as e:
        print(e)

def delete_all_audio():
    for f in os.listdir('./'):
        if f.endswith('.mp3') or f.endswith('.part'):
            os.remove(os.path.join('./', f))


def afterPlay(ctx, error, beforeMsg):
    if beforeMsg is not None:
        client.loop.create_task(beforeMsg.delete())
    if error is not None:
        print(error)

    try:
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    except Exception as e:
        print(e)
        return
    
    if (voice and not voice.is_playing()): 
        play_next(ctx, voice)

def play_next(ctx, voice):
    serverId = ctx.message.guild.id
    if len(player_queue[serverId]) > 0:
        fileName = player_queue[serverId][0]['file_name']
        delete_song_there(fileName)
        player_queue[serverId].pop(0)
        if len(player_queue[serverId]) > 0:
            next_file = player_queue[serverId][0]['file_name']
            song_title = player_queue[serverId][0]['title']
            url = player_queue[serverId][0].get('url', None)
            urlText = f'({url})' if url is not None else ''
            embed = discord.Embed(title='Playing', description=f'{song_title} {urlText}', colour=discord.Colour.blue())
            client.loop.create_task(__play_next(ctx, voice, embed, next_file))
        else:
            embed = discord.Embed(description=f'Queue is empty.', colour=discord.Colour.dark_gray())
            client.loop.create_task(ctx.send(embed=embed))
            player_current[ctx.message.guild.id] = None

async def __play_next(ctx, voice, embed, next_file):
    msg = await ctx.send(embed=embed)
    current_player = discord.FFmpegPCMAudio(next_file)
    player_current[ctx.message.guild.id] = { 'player' : current_player, 'ctx' : ctx, 'msg': msg }
    voice.play(current_player, after=lambda error: afterPlay(ctx, error, msg))

@client.command()
async def rs(ctx):
    file = random.choice(os.listdir("./effects")) 
    file_name = file.split('.')[0]
    await fx(ctx, file_name)

async def meme_list(ctx):
    meme_list = os.listdir("./effects")
    if len(meme_list) > 0:
        queue_title = "Meme List (Use with -fx [name]):"
        queue_list = ''
        for meme in meme_list:
            title = meme.split('.')[0]
            text = f"- {title}\n"
            queue_list += text
        embed = discord.Embed(title=queue_title, description=queue_list, colour=discord.Colour.blurple())
        await ctx.send(embed=embed)
        
@client.command()
async def fxl(ctx):
    await meme_list(ctx)

@client.command()
async def ml(ctx):
    await meme_list(ctx)

@client.command()
async def meme(ctx, name):
    await fx(ctx, name)

@client.command()
async def m(ctx, name):
    await fx(ctx, name)

@client.command()
async def fx(ctx, name):
    if not os.path.isfile(f'./effects/{name}.mp3') or name is None:
        await meme_list(ctx)
        return
    serverId = ctx.message.guild.id
    if not (serverId in player_queue.keys()):
        player_queue[serverId] = []
    
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    
    if voice:
        if voice.is_playing():
            voice.pause()
    else:
        try:
            voiceChannel = ctx.author.voice.channel
        except Exception as e:
            embed = discord.Embed(description="Please join any channel to start playing")
            await ctx.send(embed=embed)
            return

        await voiceChannel.connect()

    current_player = player_current.get(ctx.guild.id, None)
    embed = discord.Embed(title='Playing SFX', description=f'{name}.mp3', colour=discord.Colour.blue())
    msg = await ctx.send(embed=embed)

    def play_after_speak():
        client.loop.create_task(msg.delete())
        if current_player is not None:
            voice.play(current_player['player'], after=lambda error: afterPlay(current_player['ctx'], error, current_player['msg']))
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice.play(discord.FFmpegPCMAudio(f'./effects/{name}.mp3'), after=lambda error: play_after_speak())

@client.command()
async def p(ctx, url : str, *args):
    await play(ctx, url, args)
    
@client.command()
async def play(ctx, src : str, *args):
    audio_id = uuid.uuid4().hex
    isUrl = True
    try:
        status = urllib.request.urlopen(src).getcode()
        isUrl = status == 200 and len(args[0]) == 0
    except:
        isUrl = False
        
    lookup_opts = {
        "simulate": True,
        "quiet" : True,
        'cachedir' : False,
    }

    with youtube_dl.YoutubeDL(lookup_opts) as ydlookup:
        if isUrl:
            try:
                embed = discord.Embed(title=f'Searching with: {src}', colour=discord.Colour.dark_green())
                msg = await ctx.send(embed=embed)
                info_dict = ydlookup.extract_info(src)
            except Exception as e:
                print(e)
                await msg.delete()
                await ctx.send("An error occured downloading that video! Are you sure that URL is correct?")
                return
            
            entries = info_dict.get('entries', None)

            if entries is None:
                url = info_dict['webpage_url']
                video_title = info_dict.get('title', None)
            else:
                await msg.delete()
                await addSongFromPlaylist(ctx, entries)
                return
        else: 
            arg_string = ' '.join(args[0])
            search_word = f'{src} {arg_string}'
            embed = discord.Embed(title=f'Searching with: {search_word}', colour=discord.Colour.dark_green())
            msg = await ctx.send(embed=embed)
            info_dict = ydlookup.extract_info(f"ytsearch:{search_word}", download=False)
            url = info_dict['entries'][0]['webpage_url']
            video_title =  info_dict['entries'][0].get('title', None)

    def callback(d):
        if d['status'] == 'finished':
            client.loop.create_task(msg.delete())
            client.loop.create_task(onFinishDownloadedAudio(ctx, audio_id, video_title, url))
            
    ydl_download_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'retries' : 1,
        'cachedir' : False,
        'outtmpl': f'{audio_id}.mp3',
        'progress_hooks': [callback],
    }

    with youtube_dl.YoutubeDL(ydl_download_opts) as ydDownload:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ydDownload.download([url]))
        except Exception as e:
            print(e)
            embed = discord.Embed(title='There is an error occurred, Please try again later.', colour=discord.Colour.red())
            await ctx.send(embed=embed)

async def addSongFromPlaylist(ctx, entries):
    embed = discord.Embed(title='Processing the playlist', colour=discord.Colour.dark_green())
    processMsg = await ctx.send(embed=embed)
    mapped = list(map(lambda x: x, entries))
    for idx, item in enumerate(mapped):
        embed = discord.Embed(title=f'Playlist Loading: {idx+1}/{len(mapped)}', colour=discord.Colour.dark_green())
        msg = await ctx.send(embed=embed)

        audio_id = uuid.uuid4().hex
        url = item['webpage_url']
        
        def callback(d):
            if d['status'] == 'finished':
                client.loop.create_task(onFinishDownloadedAudio(ctx, audio_id, item['title'], url))
            
        ydl_download_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'retries' : 1,
            'cachedir' : False,
            'outtmpl': f'{audio_id}.mp3',
            'progress_hooks': [callback],
        }

        with youtube_dl.YoutubeDL(ydl_download_opts) as ydDownload:
            delete_song_there(ydl_download_opts['outtmpl'])
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: ydDownload.download([url]))
            except Exception as e:
                print(e)
                embed = discord.Embed(title='There is an error occurred, Please try again later.', colour=discord.Colour.red())
                await ctx.send(embed=embed)  

        await msg.delete()
    await processMsg.delete()

 
async def onFinishDownloadedAudio(ctx, audio_name, title, url):
    serverId = ctx.message.guild.id
    if discord.utils.get(client.voice_clients, guild=ctx.guild) is None:
        try:
            voiceChannel = ctx.author.voice.channel
        except Exception as e:
            embed = discord.Embed(description="Please join any channel to start playing")
            await ctx.send(embed=embed)
            return

        await voiceChannel.connect()
    
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)

    current_player = player_current.get(serverId, None)

    if not (serverId in player_queue.keys()):
        player_queue[serverId] = []
    player_queue[serverId].append({ "file_name": f'{audio_name}.mp3', "title": title, 'url': url })
    song_title = player_queue[serverId][-1]['title']
    if len(player_queue[serverId]) > 0 and (voice and not voice.is_playing()) and current_player is None: 
        print(f"Playing => {song_title}")
        embed = discord.Embed(title='Playing', description=f'{song_title} ({url})', colour=discord.Colour.blue())
        msg = await ctx.send(embed=embed)
        current_player = discord.FFmpegPCMAudio(player_queue[serverId][0]['file_name'])
        player_current[ctx.message.guild.id] = { 'player' : current_player, 'ctx' : ctx, 'msg': msg }
        voice.play(current_player, after=lambda error: afterPlay(ctx, error, msg))
        return
    print(f"Adding => {song_title}")
    embed = discord.Embed(title='Adding', description=f'{song_title} ({url})', colour=discord.Colour.blue())
    await ctx.send(embed=embed)

@client.command()
async def join(ctx):
    await __join(ctx, client)

@client.command()
async def leave(ctx):
    await __leave(ctx, client)


@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        embed = discord.Embed(description="Paused.", colour=discord.Colour.orange())
        await ctx.send(embed=embed)
        voice.pause()
    else:
        embed = discord.Embed(description=f'Currently no audio is playing.', colour=discord.Colour.darker_grey())
        await ctx.send(embed=embed)

@client.command()
async def remove(ctx, index):
    serverId = ctx.message.guild.id
    try:
        idx = int(index)
    except:
        embed = discord.Embed(description=f'Please insert Track Number!', colour=discord.Colour.orange())
        await ctx.send(embed=embed)
        return

    if idx  == 1:
        await skip(ctx) 
    elif player_queue[serverId][idx-1]:
        song = player_queue[serverId][idx-1]
        title = song['title']
        fileName = song['file_name']
        embed = discord.Embed(description=f"Remove {title}.", colour=discord.Colour.red())
        await ctx.send(embed=embed)
        delete_song_there(fileName)
        player_queue[serverId].pop(idx-1)

@client.command()
async def rm(ctx, index):
    await remove(ctx, index)

@client.command()
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
        embed = discord.Embed(description="Resume the audio." , colour=discord.Colour.blue())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="The audio is not paused.", colour=discord.Colour.orange())
        await ctx.send(embed=embed)

@client.command()
async def stop(ctx):
    serverId = ctx.message.guild.id
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    player_queue[serverId] = []
    player_current[ctx.message.guild.id] = None
    if voice:
        voice.stop()
    embed = discord.Embed(description="Stop the audio and Clear all song in queue", colour=discord.Colour.red())
    await ctx.send(embed=embed)

@client.command()
async def skip(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice.stop()   
    embed = discord.Embed(description="Skipping", colour=discord.Colour.orange())
    await ctx.send(embed=embed)

@client.command()
async def isus(ctx):
    await fx(ctx, 'isus')
    await ctx.message.delete()

@client.command()
async def isus_legacy(ctx):
    serverId = ctx.message.guild.id
    if not (serverId in player_queue.keys()):
        player_queue[serverId] = []

    if len(player_queue[serverId]) > 0:
        player_queue[serverId].insert(1, { "file_name": "./effects/isus.mp3", "title": "น้าค่อมกำลังอวยพรคุณ" })
        await skip(ctx)
    else:
        if discord.utils.get(client.voice_clients, guild=ctx.guild) is None:
            try:
                voiceChannel = ctx.author.voice.channel
            except Exception as e:
                embed = discord.Embed(description="Please join any channel to start playing")
                await ctx.send(embed=embed)
                return

            await voiceChannel.connect()

        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        player_queue[serverId].append({ "file_name": "./effects/isus.mp3", "title": "น้าค่อมกำลังอวยพรคุณ" })
        voice.play(discord.FFmpegPCMAudio(player_queue[serverId][0]['file_name']), after=lambda error: afterPlay(ctx, error, None))
    await ctx.message.delete()

@client.command()
async def queue(ctx):
    serverId = ctx.message.guild.id
    if not (serverId in player_queue.keys()):
        embed = discord.Embed(description="Currently no song", colour=discord.Colour.dark_grey())
        await ctx.send(embed=embed)
    if len(player_queue[serverId]) > 0:
        queue_title = "Playlist:"
        queue_list = ''
        for idx, song in enumerate(player_queue[serverId]):
            title = song['title']
            text = f"{idx+1}: {title}\n"
            queue_list += text
        embed = discord.Embed(title=queue_title, description=queue_list, colour=discord.Colour.blurple())
        await ctx.send(embed=embed)
    else: 
        embed = discord.Embed(description="Currently no song", colour=discord.Colour.dark_grey())
        await ctx.send(embed=embed)

@client.command()
async def q(ctx):
    await queue(ctx)
    
@client.command()
async def greet(ctx):
    await ctx.reply(f"ว่างายจ๊า {ctx.author.mention}")

@client.event
async def on_error(event, *args, **kwargs):
    print(event)
    
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_voice_state_update(member, before, after):
    voice = discord.utils.get(client.voice_clients, guild=member.guild)
    if voice is not None:
        if before.channel != voice.channel and voice.channel == after.channel:
            tts = gTTS(f'{member.display_name} ได้เข้ามาในห้อง', lang='th')
            tts.save('./hello.mp3')
            sound = AudioSegment.from_mp3('./hello.mp3')
            louder_sound = sound + 12
            louder_sound.export('./hello.mp3', format='mp3')
            if voice.is_playing():
                voice.pause()
                current_player = player_current[member.guild.id]
                def play_after_speak():
                    voice.play(current_player['player'], after=lambda error: afterPlay(current_player['ctx'], error, current_player['msg']))
                voice.play(discord.FFmpegPCMAudio("./hello.mp3"), after=lambda error: play_after_speak())
            else:
                voice.play(discord.FFmpegPCMAudio("./hello.mp3"))
        if before.channel == voice.channel and voice.channel != after.channel:
            tts = gTTS(f'{member.display_name} ได้ออกจากห้อง', lang='th')
            tts.save('./bye.mp3')
            sound = AudioSegment.from_mp3('./bye.mp3')
            louder_sound = sound + 12
            louder_sound.export('./bye.mp3', format='mp3')
            if voice.is_playing():
                voice.pause()
                current_player = player_current[member.guild.id]
                def play_after_speak():
                    voice.play(current_player['player'], after=lambda error: afterPlay(current_player['ctx'], error, current_player['msg']))
                voice.play(discord.FFmpegPCMAudio("./bye.mp3"), after=lambda error: play_after_speak())
            else:
                voice.play(discord.FFmpegPCMAudio("./bye.mp3"))

try:
    client.run(BOT_TOKEN)
except Exception as e:
    print(e)
finally:
    delete_all_audio()