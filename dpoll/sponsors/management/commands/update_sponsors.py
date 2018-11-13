from django.core.management.base import BaseCommand

from lightsteem.client import Client
from lightsteem.helpers.amount import Amount
from django.conf import settings

from sponsors.models import Sponsor

BLACKLIST = [
    'blocktrades',
    'trdaily',
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        client = Client()
        acc = client.account(settings.CURATION_BOT_ACCOUNT)
        for op in acc.history(
                filter=["delegate_vesting_shares"],
                order="asc",
        ):
            if op.get("delegator") == settings.CURATION_BOT_ACCOUNT:
                continue

            if op.get("delegator") in BLACKLIST:
                continue

            try:
                sponsor = Sponsor.objects.get(username=op.get("delegator"))
            except Sponsor.DoesNotExist:
                sponsor = Sponsor(
                    username=op.get("delegator"),
                )
            sponsor.delegation_amount = Amount(op.get("vesting_shares")).amount
            sponsor.save()

            print(f"Delegation of {op['delegator']}:"
                  f" {op['vesting_shares']} is saved.")
