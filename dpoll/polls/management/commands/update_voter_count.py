from django.core.management.base import BaseCommand
from polls.models import Question


class Command(BaseCommand):
    def handle(self, *args, **options):
        questions = Question.objects.all()
        for question in Question.objects.all():
            question.update_voter_count()
            question.save()
            print(f"{question} updated.")