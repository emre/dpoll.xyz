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


def steem_per_mvests():
    c = LightsteemClient()
    info = c.get_dynamic_global_properties()
    return (float(Amount(info["total_vesting_fund_steem"]).amount) /
            (float(Amount(info["total_vesting_shares"]).amount) / 1e6))


def vests_to_sp(steem_per_mvest, vests):
    return vests / 1e6 * steem_per_mvest


class Command(BaseCommand):
    """A management command to update account data from the blockchain.

    Currently we update
        - sp
        - post_count
        - reputation
        - account_age
    """
    def handle(self, *args, **options):
        steem_per_mvest = steem_per_mvests()
        users = User.objects.all()
        c = LightsteemClient(nodes=["https://api.steemit.com"])
        for chunk in chunks(users, 500):
            account_details = c.get_accounts([c.username for c in chunk])
            for account_detail in account_details:
                try:
                    related_user = User.objects.get(
                        username=account_detail["name"])
                except User.DoesNotExist:
                    print(f"{account_detail['name']} is not found. Skipping.")
                    continue

                acc = Account(c)
                acc.raw_data = account_detail

                # calculate SP
                sp = vests_to_sp(
                    steem_per_mvest,
                    float(Amount(account_detail["vesting_shares"])))

                # calculate account age in days
                account_age = (
                                      now() - addTzInfo(
                                  parse(account_detail["created"]))
                              ).total_seconds() / 86400

                related_user.sp = sp
                related_user.reputation = acc.reputation(precision=4)
                related_user.post_count = account_detail["post_count"]
                related_user.account_age = account_age
                related_user.save()
                print(f"{related_user.username} is updated.")
