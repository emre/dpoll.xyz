import uuid
import copy
import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils.text import slugify
from steemconnect.client import Client
from steemconnect.operations import CommentOptions, Comment
from django.utils.timezone import now
from .post_templates import get_body
from lightsteem.client import Client as LightSteemClient


from .models import Question, Choice

_sc_client = None


def get_sc_client():
    global _sc_client
    if not _sc_client:
        _sc_client = Client(
            client_id=settings.SC_CLIENT_ID,
            client_secret=settings.SC_CLIENT_SECRET)

    return _sc_client


def remove_duplicates(_list):
    """
    A helper function to remove duplicate
    elements from a list and keeps the list order.
    list(set(list... usage loses the order.
    """
    new_list = []
    for element in _list:
        if element not in new_list:
            new_list.append(element)
    return new_list


def get_comment(request, question, choices, permlink, tags=None):
    post_tags = copy.copy(settings.DEFAULT_TAGS)
    if tags:
        post_tags += tags

    comment = Comment(
        author=request.user.username,
        permlink=question.permlink,
        body=get_body(
            question, choices, request.user.username, permlink,
        ),
        title=question.text,
        parent_permlink=settings.COMMUNITY_TAG,
        json_metadata={
            "tags": post_tags,
            "app": f"dpoll/{settings.DPOLL_APP_VERSION}",
            "content_type": "poll",
            "question": question.text,
            "description": question.description or "",
            "choices": choices,
            "expire_at": str(question.expire_at),
            "allow_multiple_choices": str(question.allow_multiple_choices),
        }
    )

    return comment


def get_comment_options(parent_comment, reward_option=None):
    beneficiaries = []
    for account, weight in settings.BENEFICIARY_ACCOUNTS.items():
        beneficiaries.append(
            {'account': account, 'weight': weight},
        )

    params = {
        "parent_comment": parent_comment,
        "extensions": [[0, {'beneficiaries': beneficiaries}]],
    }

    # default values
    # %50 SBD/%50 SP and maximum accepted payout
    percent_steem_dollars = 10000
    max_accepted_payout = "1000000.000 SBD"
    if reward_option:
        if reward_option == "100%":
            percent_steem_dollars = 0
        elif reward_option == "0%":
            max_accepted_payout = "0.000 SBD"

    params.update({
        "percent_steem_dollars": percent_steem_dollars,
        "max_accepted_payout": max_accepted_payout,
    })

    return CommentOptions(**params)


def get_top_dpollers():
    with connection.cursor() as cursor:
        cursor.execute("select count(1), username from polls_question"
                       " group by username order by count(1) desc limit 5;")
        row = cursor.fetchall()

    return row


def get_top_voters():
    with connection.cursor() as cursor:
        cursor.execute("select count(1), user_id from polls_choice_voted_users "
                       "group by user_id order by count(1) desc limit 5;")
        row = cursor.fetchall()
    voter_list = []
    for vote_count, voter_user_id in row:
        voter_list.append(
            (vote_count, get_user_model().objects.get(pk=voter_user_id)))

    return voter_list


def validate_input(request):
    error = False
    required_fields = ["question", "expire-at"]
    for field in required_fields:
        if not request.POST.get(field):
            error = True
            messages.add_message(
                request,
                messages.ERROR,
                f"{field} field is required."
            )
    question = request.POST.get("question")
    choices = request.POST.getlist("answers[]")
    expire_at = request.POST.get("expire-at")
    tags = request.POST.get("tags")
    reward_option = request.POST.get("reward-option")
    allow_multiple_choices = request.POST.get(
        "allow-multiple-choices") == 'yes'

    # %100 -> Full Power-up
    # %50 -> Half SBD, Half SP
    # %0 -> Decline payouts
    if reward_option and reward_option not in ["100%", "50%", "0%"]:
        messages.add_message(
            request,
            messages.ERROR,
            "Invalid reward option."
        )
        error = True

    if tags:
        tags = tags.split(',')

    if question:
        if not (4 < len(question) < 256):
            messages.add_message(
                request,
                messages.ERROR,
                "Question text should be between 6-256 chars."
            )
            error = True
    choices = remove_duplicates(choices)
    choices = [c for c in choices if c]
    if len(choices) < 2:
        messages.add_message(
            request,
            messages.ERROR,
            f"At least 2 answers are required."
        )
        error = True
    elif len(choices) > 64:
        messages.add_message(
            request,
            messages.ERROR,
            f"Maximum number of answers is 64."
        )
        error = True

    if 'expire-at' in request.POST:
        if expire_at not in ["1_week", "1_month"]:
            messages.add_message(
                request,
                messages.ERROR,
                f"Invalid expiration value."
            )
            error = True

    days = 7 if expire_at == "1_week" else 30

    permlink = slugify(question)[0:256]
    if not permlink:
        permlink = str(uuid.uuid4())

    return error, question, choices, expire_at, permlink, days, tags,\
           allow_multiple_choices


def add_or_get_question(request, question_text, permlink, days,
                        allow_multiple_choices):
    try:
        question = Question.objects.get(
            username=request.user.username,
            permlink=permlink,
        )
        question.text = question_text
        question.description = request.POST.get("description")
        question.expire_at = now() + timedelta(days=days)
        question.allow_multiple_choices = allow_multiple_choices
    except Question.DoesNotExist:
        question = Question(
            text=question_text,
            username=request.user.username,
            description=request.POST.get("description"),
            permlink=permlink,
            expire_at=now() + timedelta(days=days),
            allow_multiple_choices=allow_multiple_choices,
        )
    question.save()
    return question


def add_choices(question, choices, flush=False):
    if flush:
        Choice.objects.filter(question=question).delete()
    for choice in choices:
        choice_instance = Choice(
            question=question,
            text=choice,
        )
        choice_instance.save()


def fetch_poll_data(author, permlink):
    """
    Fetch a poll from the blockchain and return the poll metadata.
    """
    c = LightSteemClient()
    content = c.get_content(author, permlink)
    if content.get("id") == 0:
        raise ValueError("Not a valid blockchain Comment object")
    metadata = json.loads(content.get("json_metadata"))
    if not metadata:
        raise ValueError("Not a poll")
    if metadata.get("content_type") != "poll":
        raise ValueError("Not a poll")

    votes_casted = False
    comments = c.get_content_replies(author, permlink)
    for comment in comments:
        if not comment.get("json_metadata"):
            continue
        json_metadata = json.loads(comment.get("json_metadata"))
        try:
            if json_metadata and json_metadata.get("content_type") == "poll_vote":
                votes_casted = True
        except AttributeError:
            continue

    return {
        "question": metadata.get("question"),
        "description": metadata.get("description"),
        "answers": metadata.get("choices"),
        "tags": metadata.get("tags"),
        "votes_casted": votes_casted,
    }


def sanitize_filter_value(val):
    if not val:
        return
    try:
        return int(val)
    except ValueError:
        return


