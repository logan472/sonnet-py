# User update tracking
# Ultrabear 2021

import importlib

import discord, time
from datetime import datetime

import lib_loaders

importlib.reload(lib_loaders)
import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)

from lib_db_obfuscator import db_hlapi
from lib_loaders import inc_statistics

from typing import Any


async def catch_logging_error(channel: discord.TextChannel, embed: discord.Embed) -> None:
    try:
        await channel.send(embed=embed)
    except discord.errors.Forbidden:
        pass


async def on_member_update(before: discord.Member, after: discord.Member, **kargs: Any) -> None:

    inc_statistics([before.guild.id, "on-member-update", kargs["kernel_ramfs"]])

    with db_hlapi(before.guild.id) as db:
        username_log = db.grab_config("username-log")

    if username_log and (channel := kargs["client"].get_channel(int(username_log))):
        if before.nick == after.nick:
            return

        message_embed = discord.Embed(title="Nickname updated", color=0x008744)
        message_embed.set_author(name=f"{before} ({before.id})", icon_url=before.avatar_url)
        message_embed.add_field(name=f"Before | {bool(before.nick)}", value=before.nick)
        message_embed.add_field(name=f"After | {bool(after.nick)}", value=after.nick)

        message_embed.timestamp = datetime.utcnow()
        message_embed.set_footer(text=f"unix: {int(time.time())}")

        await catch_logging_error(channel, message_embed)


def parsedate(indata: datetime) -> str:
    return f"{time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(datetime.timestamp(indata)))} ({(datetime.utcnow() - indata).days} days ago)"


async def on_member_join(member: discord.Member, **kargs: Any) -> None:

    inc_statistics([member.guild.id, "on-member-join", kargs["kernel_ramfs"]])

    with db_hlapi(member.guild.id) as db:
        if joinlog := db.grab_config("join-log"):
            if logging_channel := kargs["client"].get_channel(int(joinlog)):

                embed = discord.Embed(title=f"{member} joined.", description=f"*{member.mention} joined the server.*", color=0x758cff)
                embed.set_thumbnail(url=member.avatar_url)

                embed.timestamp = datetime.utcnow()
                embed.set_footer(text=f"uid: {member.id}, unix: {int(time.time())}")

                embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)

                await catch_logging_error(logging_channel, embed)


async def on_member_remove(member: discord.Member, **kargs: Any) -> None:

    inc_statistics([member.guild.id, "on-member-remove", kargs["kernel_ramfs"]])

    with db_hlapi(member.guild.id) as db:
        if joinlog := db.grab_config("join-log"):
            if logging_channel := kargs["client"].get_channel(int(joinlog)):

                embed = discord.Embed(title=f"{member} left.", description=f"*{member.mention} left the server.*", color=0xffe875)
                embed.set_thumbnail(url=member.avatar_url)

                embed.timestamp = datetime.utcnow()
                embed.set_footer(text=f"uid: {member.id}, unix: {int(time.time())}")

                embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)
                embed.add_field(name="Joined", value=parsedate(member.joined_at), inline=True)

                await catch_logging_error(logging_channel, embed)


category_info = {'name': 'UserUpdate'}

commands = {
    "on-member-update": on_member_update,
    "on-member-join": on_member_join,
    "on-member-remove": on_member_remove,
    }

version_info: str = "1.2.3-DEV"
