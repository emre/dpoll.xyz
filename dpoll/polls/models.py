from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    token = models.TextField(blank=True, null=True)


class Question(models.Model):
    text = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField('Expiration date')
    username = models.CharField(max_length=255)
    permlink = models.CharField(max_length=255, blank=True, null=True,
                                db_index=True)

    def __str__(self):
        return self.text

    class Meta:
        unique_together = ('username', 'permlink')

    def is_votable(self):
        return self.expire_at > timezone.now()


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    voted_users = models.ManyToManyField(User)

    @property
    def votes(self):
        return self.voted_users.all().count()

    def __str__(self):
        return self.text
