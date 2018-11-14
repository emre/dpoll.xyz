import asyncio
import json
import logging
import random
import uuid
from datetime import datetime

import discord
from dateutil.parser import parse
from discord.ext import commands
from django.conf import settings
from django.core.management.base import BaseCommand
from lightsteem.client import Client as LightsteemClient
from lightsteem.datastructures import Operation
from polls.models import Question

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


async def my_background_task():
    """
    Check the VP constantly.
    If the VP is greater than %95, then vote randomly on dpoll voters.
    """
    channel = discord.Object(settings.DISCORD_CURATION_CHANNEL_ID)

    await bot.wait_until_ready()
    while not bot.is_closed:
        try:
            acc = lightsteem_client.account(settings.CURATION_BOT_ACCOUNT)
            if acc.vp() > 95:
                questions = Question.objects.all().order_by(
                    "-id").values_list('username', 'permlink')[0:25]
                eligible_comments = []
                seen_authors = set()
                for author, permlink in questions:
                    comments = lightsteem_client.get_content_replies(author, permlink)
                    for comment in comments:
                        try:
                            metadata = json.loads(comment.get("json_metadata", "{}"))
                        except Exception as e:
                            continue
                        if metadata.get("content_type") != "poll_vote":
                            continue
                        created_at = parse(comment["created"])
                        if (datetime.utcnow() - created_at).total_seconds() > 432000:
                            # Do not vote the posts older than 5 days.
                            continue

                        # Skip the comment if we already voted on that.
                        voters = [v["voter"] for v in comment["active_votes"]]
                        if settings.CURATION_BOT_ACCOUNT in voters:
                            continue

                        if comment["author"] in seen_authors:
                            continue

                        eligible_comments.append((
                            comment["author"], comment["permlink"]))
                        seen_authors.add(comment["author"])

                print(len(eligible_comments), "comments found")
                if len(eligible_comments):
                    random.shuffle(eligible_comments)
                    eligible_comment = eligible_comments[0]
                    vote_op = Operation('vote', {
                        'voter': settings.CURATION_BOT_ACCOUNT,
                        'author': eligible_comment[0],
                        'permlink': eligible_comment[1],
                        'weight': 100 * 50
                    })
                    lightsteem_client.broadcast(vote_op)
                    await bot.send_message(
                        channel,
                        f"Lucky strike: {eligible_comment[0]}/{eligible_comment[1]}")
        except Exception as e:
            print(e)
        # re-run in every 5 mins
        await asyncio.sleep(300)


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

    # only members of 'team members' group can use the bot.
    if 'team members' not in [r.name for r in ctx.message.author.roles]:
        await bot.say("You don't have required permissions to do that.")
        return

    try:
        vote_op = Operation('vote', {
            'voter': settings.CURATION_BOT_ACCOUNT,
            'author': post_content.get("author"),
            'permlink': post_content.get("permlink"),
            'weight': weight * 100
        })
        if post_content.get("depth") == 0:
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
        else:
            lightsteem_client.broadcast(vote_op)

        await bot.say(f"Voted. Current VP: {vp}")
    except Exception as error:
        await bot.say(str(error))


class Command(BaseCommand):
    def handle(self, *args, **options):
        bot.loop.create_task(my_background_task())
        bot.run(settings.CURATION_BOT_DISCORD_TOKEN)
