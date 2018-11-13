from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model

from steemconnect.client import Client
from steemconnect.operations import CommentOptions

_sc_client = None


def get_sc_client():
    global _sc_client
    if not _sc_client:
        _sc_client = Client(
            client_id=settings.SC_CLIENT_ID,
            client_secret=settings.SC_CLIENT_SECRET)

    return _sc_client


def get_comment_options(parent_comment):
    beneficiaries = [
        {'account': settings.BENEFICIARY_ACCOUNT, 'weight': 500},
    ]

    return CommentOptions(
        parent_comment=parent_comment,
        extensions=[[0, {'beneficiaries': beneficiaries}]],
        allow_curation_rewards=True,
    )


def get_top_dpollers():
    with connection.cursor() as cursor:
        cursor.execute("select count(1), username from polls_question"
                       " group by username order by count(1) desc limit 10;")
        row = cursor.fetchall()

    return row


def get_top_voters():
    with connection.cursor() as cursor:
        cursor.execute("select count(1), user_id from polls_choice_voted_users "
                       "group by user_id order by count(1) desc limit 10;")
        row = cursor.fetchall()
    voter_list = []
    for vote_count, voter_user_id in row:
        voter_list.append(
            (vote_count, get_user_model().objects.get(pk=voter_user_id)))

    return voter_list
