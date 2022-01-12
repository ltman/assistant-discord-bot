import discord

async def __join(ctx, client):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice is not None:
        await voice.disconnect()
    try:
        voiceChannel = ctx.author.voice.channel
    except Exception as e:
        embed = discord.Embed(description="You are not in any room!", colour=discord.Colour.red())
        await ctx.send(embed=embed)
        return

    await voiceChannel.connect()