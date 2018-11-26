from django.core.management.base import BaseCommand

from lightsteem.client import Client
from lightsteem.helpers.amount import Amount
from django.conf import settings

from dateutil.parser import parse
from base.utils import add_tz_info

from sponsors.models import Sponsor

# paid delegations are not counted as sponsors
BLACKLIST = [
    'blocktrades',
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        client = Client()
        acc = client.account(settings.CURATION_BOT_ACCOUNT)
        for index, transaction in acc.history(
                filter=["delegate_vesting_shares"],
                order="asc",
                only_operation_data=False,
        ):
            op = transaction["op"][1]
            if op.get("delegator") == settings.CURATION_BOT_ACCOUNT:
                continue

            if op.get("delegator") in BLACKLIST:
                continue

            try:
                sponsor = Sponsor.objects.get(username=op.get("delegator"))
                sponsor.delegation_modified_at = add_tz_info(
                    parse(transaction["timestamp"]))
            except Sponsor.DoesNotExist:
                sponsor = Sponsor(
                    username=op.get("delegator"),
                )
                sponsor.delegation_created_at = add_tz_info(
                    parse(transaction["timestamp"]))
            sponsor.delegation_amount = Amount(op.get("vesting_shares")).amount
            sponsor.save()

            print(f"Delegation of {op['delegator']}:"
                  f" {op['vesting_shares']} is saved.")
