from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import discord
from discord.ext import commands
import logging
import uuid
import json

from dateutil.parser import parse
from datetime import datetime

from lightsteem.client import Client as LightsteemClient
from lightsteem.datastructures import Operation

from .utils import get_comment_body


client = discord.Client()
lightsteem_client = LightsteemClient(
    keys=[settings.CURATION_BOT_POSTING_KEY], loglevel=logging.DEBUG)
bot = commands.Bot(command_prefix='$', description="dPoll curation bot")


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command(pass_context=True)
async def upvote(ctx, url: str, weight: int):
    acc = lightsteem_client.account(settings.CURATION_BOT_ACCOUNT)

    if ctx.message.server.name != 'dpoll.xyz':
        return

    vp = acc.vp()
    if vp < 81:
        # Donot vote if VP is lower than %81.
        await bot.say(f"VP is not enough ({vp}). Bot needs to recharge.")
        return

    try:
        author = url.split("@")[1].split("/")[0]
        permlink = url.split("@")[1].split("/")[1]
    except IndexError as e:
        # this kind of parsing works for every dApp URL.
        await bot.say("invalid URL")
        return

    post_content = lightsteem_client.get_content(author, permlink)
    if not post_content.get("author"):
        # this case might happen if the link is valid but the post
        # doesn't exists in the blockchain.
        await bot.say("Invalid post")
        return

    # Only reward comments/posts created on dPoll
    json_metadata = json.loads(post_content.get("json_metadata", "{}"))
    if 'dpoll' not in json_metadata.get("tags", []):
        await bot.say("This post doesn't have required tag: dpoll")
        return

    created_at = parse(post_content.get("created"))
    if (datetime.utcnow() - created_at).total_seconds() < 840:
        # This check is required to maximize curation rewards.
        await bot.say("Posts are eligible for an upvote after 14 mins.")
        return

    voters = [v["voter"] for v in post_content.get("active_votes")]
    # if we already voted, there is no need to vote again.
    if settings.CURATION_BOT_ACCOUNT in voters:
        await bot.say(f'Already voted that poll.')
        return

    # only members of 'curators' group can use the bot.
    if 'curators' not in [r.name for r in ctx.message.author.roles]:
        await bot.say("You don't have required permissions to do that.")
        return

    try:
        vote_op = Operation('vote', {
            'voter': settings.CURATION_BOT_ACCOUNT,
            'author': post_content.get("author"),
            'permlink': post_content.get("permlink"),
            'weight': weight * 100
        })

        comment_op = Operation('comment', {
            "parent_author": post_content.get("author"),
            "parent_permlink": post_content.get("permlink"),
            "author": settings.CURATION_BOT_ACCOUNT,
            "permlink": str(uuid.uuid4()),
            "title": None,
            "body": get_comment_body(ctx.message.author.display_name),
            "json_metadata": None,
        })
        lightsteem_client.broadcast([vote_op, comment_op])

        await bot.say(f"Voted. Current VP: {vp}")
    except Exception as error:
        await bot.say(str(error))


class Command(BaseCommand):
    def handle(self, *args, **options):
        bot.run(settings.CURATION_BOT_DISCORD_TOKEN)

