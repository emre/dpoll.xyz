from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    token = models.TextField(blank=True, null=True)


class Question(models.Model):
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    expire_at = models.DateTimeField('Expiration date')
    user = models.ForeignKey(User, blank=True, null=True,
                             on_delete=models.CASCADE)
    permlink = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.text

    def is_votable(self):
        return self.expire_at < timezone.now()


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.text
