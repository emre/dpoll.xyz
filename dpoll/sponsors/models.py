from django.db import models
from django.utils import timezone


class Sponsor(models.Model):
    username = models.CharField(max_length=255)
    delegation_amount = models.FloatField()
    opt_in_to_rewards = models.BooleanField(default=True)
    created_at = models.DateTimeField(editable=False)
    modified_at = models.DateTimeField()
    delegation_created_at = models.DateTimeField(blank=True, null=True)
    delegation_modified_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.modified_at = timezone.now()
        return super(Sponsor, self).save(*args, **kwargs)

    def __str__(self):
        return self.username
