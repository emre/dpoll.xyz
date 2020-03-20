import getpass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils.timezone import now
from lightsteem.client import Client
from lightsteem.datastructures import Operation
from lightsteem.helpers.amount import Amount
from sponsors.models import Sponsor

"""
Flow:
    - Get delegators delegating at least 1 week and calculate their share
    - Get the rewards (in liquid) total
    - Send payments
    This flow has some downsides but considering the development time and the
    delegator volume, it sounds like the best solution.
"""


class Command(BaseCommand):
    def handle(self, *args, **options):
        active_key = getpass.getpass(
            f"Active key of f{settings.SPONSORS_ACCOUNT}")
        client = Client(keys=[active_key, ], nodes=["https://api.hivekings.com"])
        account = client.account(settings.SPONSORS_ACCOUNT)
        one_week_ago = now() - timedelta(days=7)
        sponsors = Sponsor.objects.filter(
            delegation_created_at__lt=one_week_ago,
            delegation_amount__gt=0,
            opt_in_to_rewards=True,
        )
        print(f"{sponsors.count()} sponsors found.")
        total_shares = Sponsor.objects.aggregate(
            total=Sum("delegation_amount"))["total"]
        print(f"{total_shares} VESTS delegated.")
        liquid_funds = Amount(account.raw_data["balance"])
        print(f"dpoll.sponsors has {liquid_funds}.")
        one_percent_share = liquid_funds.amount / 100

        transfers = []
        for sponsor in sponsors:
            shares_in_percent = Decimal(
                sponsor.delegation_amount * 100 / total_shares)
            amount = "%.3f" % (one_percent_share * shares_in_percent)
            transfers.append({
                "from": settings.SPONSORS_ACCOUNT,
                "to": sponsor.username,
                "amount": f"{amount} STEEM",
                "memo": f"Greetings {sponsor.username},"
                        " Thank you for supporting dPoll. "
                        "Here is your weekly rewards."
            })

        op_list = [Operation('transfer', op) for op in transfers]
        client.broadcast(op_list)
        print("Rewards are sent!")
