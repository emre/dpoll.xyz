from django.db.models.signals import m2m_changed

from .models import Choice

def update_voter_count(sender, instance, **kwargs):
    """Whenever a new vote is added, recalculate the Question.voter_count
    and update the total.

    :param sender: Signal sender
    :param instance: Question instance
    """
    instance.update_voter_count()
    instance.save()

m2m_changed.connect(update_voter_count, sender=Choice.voted_users.through)