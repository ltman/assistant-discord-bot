import discord

async def __leave(ctx, client):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await voice.disconnect()
    else:
        embed = discord.Embed(description=f'The bot is not connected to a voice channel.' , colour=discord.Colour.orange())
        await ctx.send(embed=embed)