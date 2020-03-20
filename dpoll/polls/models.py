import threading
import copy
import pytz
import math
from dateutil.parser import parse
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from lightsteem.client import Client
from lightsteem.helpers.account import Account
from lightsteem.helpers.amount import Amount
from prettytable import PrettyTable
from communities.models import Community


SA_STAKE_LIMIT = 500000000


def sa_stake_based_voting_point(vests):
    point = vests
    if vests > SA_STAKE_LIMIT:
        point = SA_STAKE_LIMIT * (
                math.log10(vests) - math.log10(SA_STAKE_LIMIT) + 1)

    return float(point)


class User(AbstractUser):

    reputation = models.DecimalField(
        max_digits=6, decimal_places=4, blank=True, null=True)
    post_count = models.IntegerField(blank=True, null=True)
    sp = models.DecimalField(max_digits=64, decimal_places=4, blank=True,
                             null=True)
    vests = models.DecimalField(max_digits=64, decimal_places=6, blank=True, null=True)
    account_age = models.IntegerField(blank=True, null=True)

    @property
    def polls_created(self):
        return Question.objects.filter(
            username=self.username).order_by('-id')

    @property
    def recent_questions(self):
        return self.polls_created[0:10]

    @property
    def votes_casted(self):
        return Choice.objects.filter(
            voted_users__username=self.username).order_by('-id')

    @property
    def recent_choices(self):
        return self.votes_casted[0:10]

    @property
    def total_polls_created(self):
        return self.polls_created.count()

    @property
    def total_votes_casted(self):
        return self.votes_casted.count()

    @property
    def profile_url(self):
        return reverse('profile', args=[self.username])

    @property
    def sa_effective_vests(self):
        return sa_stake_based_voting_point(self.vests)

    def update_info(self, steem_per_mvest=None, account_detail=None):
        c = Client(nodes=["https://api.hivekings.com"])

        if not steem_per_mvest:
            # get chain properties
            dygp = c.get_dynamic_global_properties()
            steem_per_mvest =  (
                    float(Amount(dygp["total_vesting_fund_steem"]).amount) /
                    (float(Amount(dygp["total_vesting_shares"]).amount) / 1e6))

        # get account detail
        if not account_detail:
            account_detail = c.get_accounts([self.username])[0]
        vests = float(Amount(account_detail["vesting_shares"]))

        # calculate account age
        t = parse(account_detail["created"])
        if t.tzinfo is None:
            utc_time = pytz.timezone('UTC')
            t = utc_time.localize(t)

        # account reputation
        acc = Account(c)
        acc.raw_data = account_detail

        self.reputation = acc.reputation(precision=4)
        self.sp = vests / 1e6 * steem_per_mvest
        self.vests = vests
        self.account_age = (timezone.now() - t).total_seconds() / 86400
        self.post_count = account_detail["post_count"]
        self.save()

        return self

    def update_info_async(self, steem_per_mvest=None, account_detail=None):
        t = threading.Thread(
            target=self.update_info,
            kwargs={
                "steem_per_mvest": steem_per_mvest,
                "account_detail": account_detail,
            }
        )
        t.start()


def vests_to_sp(steem_per_mvest, vests):
    return vests / 1e6 * steem_per_mvest

class Question(models.Model):
    text = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField('Expiration date')
    username = models.CharField(max_length=255)
    permlink = models.CharField(max_length=255, blank=True, null=True,
                                db_index=True)
    allow_multiple_choices = models.BooleanField(default=False)
    voter_count = models.IntegerField(default=0)
    promotion_amount = models.FloatField(
        blank=True,
        null=True,
        help_text="Promotion amount in SBD")
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    @property
    def expire_at_humanized(self):
        diff_in_days = (self.expire_at - self.created_at).days
        if diff_in_days <= 7:
            return "1_week"
        else:
            return "1_month"

    class Meta:
        unique_together = ('username', 'permlink')

    def is_votable(self):
        return self.expire_at > timezone.now()

    def is_editable(self):
        """
        Two rules to decide if a Poll is editable or not:
            - Poll must be open.
            - Poll must not have any votes casted from other users.
        """
        if not self.is_votable:
            return False
        votes = Choice.objects.filter(
            question=self).aggregate(votes=models.Count('voted_users'))
        return votes["votes"] == 0

    def update_voter_count(self):
        """
        Update a Question object's voter count with the registered voters.
        Discards multiple votes from the same vote caster.
        :return (Question): self
        """
        voters = []
        for choice in self.choices.all():
            voters += choice.voted_users.values_list('username', flat=True)
        self.voter_count = len(list(set(voters)))
        return self

    def votes_summary(self, age=None, rep=None, post_count=None, sp=None,
                      stake_based=False, sa_stake_based=False, community=None):
        filter_exists = bool(rep or sp or age or post_count or community)
        choices = list(self.choices.all())

        community_members = []
        community_filter_active = community or False
        if community:
            try:
                # Check if the community really exists
                # In case it doesn't return an empty list for the community
                # members.
                community_members = Community.objects.get(
                    name=community).member_list
            except Community.DoesNotExist:
                community_filter_active = False

        # Calculate vote count
        # if the query includes filters, then exclude the non-eligible votes.
        if filter_exists:
            all_votes = int(sum(
                [c.filtered_vote_count(
                    rep, age, post_count, sp,
                    stake_based=stake_based,
                    sa_stake_based=sa_stake_based,
                    community=community_members,
                    community_filter_active=community_filter_active) for c in
                 choices]))
        else:
            if stake_based:
                # @todo: fetch this from SQL query, directly.
                all_votes = 0
                for c in choices:
                    for u in c.voted_users.all():
                        all_votes += sa_stake_based_voting_point(u.vests)
            elif sa_stake_based:
                all_votes = 0
                for c in choices:
                    for u in c.voted_users.all():
                        all_votes += sa_stake_based_voting_point(u.vests)
            else:
                all_votes = sum([c.votes for c in choices])
        choice_list = []
        choices_selected = 0
        for choice in choices:
            choice_data = choice
            if choice.votes:
                choice_data = choice_data.inject_stats(
                    filter_exists, rep, age, post_count, sp, all_votes,
                    stake_based=stake_based, sa_stake_based=sa_stake_based,
                    community=community_members,
                    community_filter_active=community_filter_active
                )
                choices_selected += 1
            else:
                choice_data.percent = 0
            choice_list.append(choice_data)
        choice_list_ordered = copy.deepcopy(choice_list)
        choice_list.sort(key=lambda x: x.percent, reverse=True)
        return choice_list, choice_list_ordered, choices_selected,\
               filter_exists, all_votes

    def audit_response(self, choice_list):
        data = PrettyTable()
        data.field_names = [
            "Choice", "Voter", "Transaction ID", "Block num",
            "Rep", "SP", "Post Count", "Account Age"]
        for choice in choice_list:
            if hasattr(choice, 'voters'):
                for user in choice.voters:
                    rep = round(user.reputation, 2)
                    sp = int(user.sp)

                    try:
                        audit = VoteAudit.objects.get(
                            question=self,
                            voter=user,
                        )
                        data.add_row(
                            [
                                choice.text,
                                user.username,
                                audit.trx_id,
                                audit.block_id,
                                rep,
                                sp,
                                user.post_count,
                                user.account_age
                            ]
                        )
                    except VoteAudit.DoesNotExist:
                        data.add_row(
                            [
                                choice.text,
                                user.username,
                                'missing',
                                'missing',
                                rep,
                                sp,
                                user.post_count,
                                user.account_age
                            ]
                        )

        return HttpResponse(f"<pre>{data}</pre>")


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE,
                                 related_name="choices")
    text = models.CharField(max_length=200)
    voted_users = models.ManyToManyField(User)

    @property
    def votes(self):
        return self.voted_users.all().count()

    def filtered_vote_count(self, rep, account_age, post_count, sp,
                            return_users=False, stake_based=False, sa_stake_based=False,
                            community=None, community_filter_active=False):

        filtered_user_count = 0
        filtered_users = []
        total_stake_in_sp = 0
        total_sa_stake_in_vests = 0
        for user in self.voted_users.all().order_by("-sp"):
            if community_filter_active:
                if user.username not in community:
                    continue

            if rep:
                try:
                    rep = int(rep)
                    if user.reputation < rep:
                        continue
                except ValueError:
                    pass

            if account_age:
                try:
                    account_age = int(account_age)
                    if user.account_age < account_age:
                        continue
                except ValueError:
                    pass
            if post_count:
                if isinstance(post_count, int):
                    if user.post_count < post_count:
                        continue
            if sp:
                try:
                    if user.sp < int(sp):
                        continue
                except ValueError:
                    pass
            filtered_user_count += 1
            total_stake_in_sp += user.sp
            total_sa_stake_in_vests += sa_stake_based_voting_point(user.vests)
            filtered_users.append(user)

        if sa_stake_based:
            returned_data = int(total_sa_stake_in_vests)
        elif stake_based:
            returned_data = int(total_stake_in_sp)
        else:
            returned_data = filtered_user_count

        if return_users:
            return returned_data, filtered_users
        return returned_data

    def inject_stats(self, filter_exists, rep, age, post_count, sp, all_votes,
                     stake_based=False, sa_stake_based=False, community=None,
                     community_filter_active=False):
        if filter_exists:
            self.vote_count, self.voters = self. \
                filtered_vote_count(
                    rep, age, post_count, sp, return_users=True,
                    stake_based=stake_based, sa_stake_based=sa_stake_based, community=community,
                    community_filter_active=community_filter_active
            )
            if self.vote_count == 0:
                self.percent = 0
            else:
                self.percent = round(
                    100 * self.vote_count / all_votes, 2)
            self.voter_count = len(self.voters)
        else:
            self.voter_count = self.voted_users.count()
            if stake_based:
                self.vote_count = sum([u.sp for u in self.voted_users.all()])
            elif sa_stake_based:
                self.vote_count = sum(
                    [sa_stake_based_voting_point(u.vests) for u in self.voted_users.all()])
            else:
                self.vote_count = self.votes
            self.percent = round(
                100 * self.vote_count / all_votes, 2)
            self.voters = self.voted_users.all().order_by("-sp")

        return self

    def __str__(self):
        return self.text


class PromotionTransaction(models.Model):
    from_user = models.CharField(max_length=255)
    amount = models.FloatField()
    trx_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    memo = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    permlink = models.CharField(max_length=255, null=True, blank=True)


class VoteAudit(models.Model):
    """Stores the blockchain references of the votes casted on dPoll.
    """
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    choices = models.ManyToManyField(Choice, blank=True)
    voter = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    block_id = models.BigIntegerField(blank=True, null=True)
    trx_id = models.TextField(blank=True, null=True)
