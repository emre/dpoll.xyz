from dateutil.parser import parse
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from lightsteem.client import Client as LightsteemClient
from lightsteem.helpers.account import Account
from lightsteem.helpers.amount import Amount
from polls.models import User

from .utils import addTzInfo


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    """A management command to update account data from the blockchain.

    Currently we update
        - sp
        - post_count
        - reputation
        - account_age
    """
    def handle(self, *args, **options):
        users = User.objects.all()
        c = LightsteemClient(nodes=["https://api.hivekings.com", "https://api.hive.blog"])
        dygp = c.get_dynamic_global_properties()
        steem_per_mvest = (
                float(Amount(dygp["total_vesting_fund_steem"]).amount) /
                (float(Amount(dygp["total_vesting_shares"]).amount) / 1e6))
        c = LightsteemClient(nodes=["https://api.hivekings.com"])
        for chunk in chunks(users, 500):
            account_details = c.get_accounts([c.username for c in chunk])
            for account_detail in account_details:
                try:
                    related_user = User.objects.get(
                        username=account_detail["name"])
                except User.DoesNotExist:
                    print(f"{account_detail['name']} is not found. Skipping.")
                    continue
                print("updating", related_user)
                related_user.update_info(
                    steem_per_mvest=steem_per_mvest,
                    account_detail=account_detail,
                )
