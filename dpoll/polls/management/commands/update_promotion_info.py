from django.core.management.base import BaseCommand
from django.utils import timezone
from polls.models import Question, PromotionTransaction
from datetime import datetime
from lightsteem.client import Client
from lightsteem.helpers.amount import Amount
from lightsteem.datastructures import Operation

from django.conf import settings

class Command(BaseCommand):
    """A management command to process promotion transaction.
    It only accepts SBD transfers. Refunds STEEM transfers automatically.
    """

    def refund(self, lightsteem_client, to, amount, memo):
        """Refunds an invalid transaction

        :param lightsteem_client: Lightsteem client instance
        :param to (str):  The account will be refunded
        :param amount (str): The amount and asset of the refund
        :param memo (str): The memo indicates the wrong behaviour
        """
        try:
            op = Operation('transfer', {
                "from": settings.PROMOTION_ACCOUNT,
                "to": to,
                "amount": amount,
                "memo": memo,
            })
            lightsteem_client.broadcast(op)
        except Exception as e:
            print(e)

    def handle(self, *args, **options):
        """Entry point for the Django management command"""
        client = Client(keys=[settings.PROMOTION_ACCOUNT_ACTIVE_KEY,], nodes=["https://api.hivekings.com"])
        acc = client.account(settings.PROMOTION_ACCOUNT)
        for _, transaction in acc.history(
                filter=["transfer"],
                only_operation_data=False,
        ):

            op = transaction["op"][1]

            # only process incoming transactions
            if op["from"] == settings.PROMOTION_ACCOUNT:
                continue

            try:
                promotion_transaction = PromotionTransaction.objects.get(
                    trx_id=transaction["trx_id"]
                )
                # if transaction already exists, means what we already
                #  processed it. so, we can skip it safely.
                print(f"This transaction is already processed."
                      f"Skipping. ({transaction['trx_id']})")
                continue
            except PromotionTransaction.DoesNotExist:
                amount = Amount(op["amount"])
                promotion_amount = '%.3f' % float(amount.amount)
                # create a base transaction first
                promotion_transaction = PromotionTransaction(
                    trx_id=transaction["trx_id"],
                    from_user=op["from"],
                    amount=promotion_amount,
                    memo=op["memo"],
                )
                promotion_transaction.save()

                # check if the asset is valid
                if amount.symbol == "STEEM":
                    print(f"Invalid Asset. Refunding. ({op['amount']})")
                    self.refund(
                        client, op["from"],
                        op["amount"], "Only SBD is accepted."
                    )
                    continue

                # check if the memo is valid
                memo = op["memo"]
                try:
                    author = memo.split("@")[1].split("/")[0]
                    permlink = memo.split("@")[1].split("/")[1]
                except IndexError as e:
                    print(f"Invalid URL. Refunding. ({memo})")
                    self.refund(
                        client, op["from"], op["amount"], "Invalid URL"
                    )
                    continue

                # check if the poll exists
                try:
                    question = Question.objects.get(
                        username=author, permlink=permlink)
                except Question.DoesNotExist:
                    print(f"Invalid poll. Refunding. ({memo})")
                    self.refund(
                        client, op["from"], op["amount"], "Invalid poll."
                    )
                    continue

                # if the poll is closed, don't mind promoting it.
                if question.expire_at < timezone.now():
                    print(f"Expired poll. Refunding. ({memo})")
                    self.refund(
                        client, op["from"], op["amount"], "Expired poll."
                    )
                    continue

                promotion_transaction.author = author
                promotion_transaction.permlink = permlink
                promotion_transaction.save()

                # update the related poll's promotion amount
                if not question.promotion_amount:
                    question.promotion_amount = float(amount.amount)
                else:
                    question.promotion_amount += float(amount.amount)
                question.save()

                print(f"{author}/{permlink} promoted with "
                      f"{promotion_amount} STEEM.")
