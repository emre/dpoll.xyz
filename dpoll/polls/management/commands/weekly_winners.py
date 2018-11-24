from django.core.management.base import BaseCommand, no_translations
from dateutil.parser import parse

from polls.models import Question
import operator

from .utils import addTzInfo


class Command(BaseCommand):

    @no_translations
    def handle(self, *args, **options):
        start_time = addTzInfo(parse(options.get("start_time")))
        end_time = addTzInfo(parse(options.get("end_time")))

        polls = {}
        for question in Question.objects.filter(
                created_at__gt=start_time, created_at__lt=end_time):
            vote_count = 0
            for choice in question.choice_set.all():
                for user in choice.voted_users.all():
                    vote_count += 1
            polls.update({
                f"{question.username}/{question.permlink}": vote_count})

        sorted_polls = sorted(
            polls.items(), key=operator.itemgetter(1))
        sorted_polls.reverse()
        for i, sorted_poll in enumerate(sorted_polls[0:10]):
            print(f"{i}. {sorted_poll}")

    def add_arguments(self, parser):
        parser.add_argument(
            'start_time', type=str)
        parser.add_argument(
            'end_time', type=str)

