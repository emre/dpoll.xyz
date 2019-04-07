from django.db import models


class Community(models.Model):
    name = models.CharField("Community name", max_length=255)
    owners = models.ManyToManyField("polls.User", blank=True)
    members = models.TextField(blank=True, null=True)

    @property
    def member_list(self):
        return "\n".join(self.members)

    def __str__(self):
        return self.name