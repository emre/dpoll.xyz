
from django.conf import settings
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
    )
