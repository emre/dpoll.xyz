import uuid
import copy
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
        }
    )

    return comment


def get_comment_options(parent_comment):
    beneficiaries = []
    for account, weight in settings.BENEFICIARY_ACCOUNTS.items():
        beneficiaries.append(
            {'account': account, 'weight': weight},
        )

    return CommentOptions(
        parent_comment=parent_comment,
        extensions=[[0, {'beneficiaries': beneficiaries}]],
        allow_curation_rewards=True,
    )


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
    elif len(choices) > 20:
        messages.add_message(
            request,
            messages.ERROR,
            f"Maximum number of answers is 20."
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

    return error, question, choices, expire_at, permlink, days, tags


def add_or_get_question(request, question_text, permlink, days):
    try:
        question = Question.objects.get(
            username=request.user.username,
            permlink=permlink,
        )
        question.text = question_text
        question.description = request.POST.get("description")
        question.expire_at = now() + timedelta(days=days)
    except Question.DoesNotExist:
        question = Question(
            text=question_text,
            username=request.user.username,
            description=request.POST.get("description"),
            permlink=permlink,
            expire_at=now() + timedelta(days=days),
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
