from django.db import models


class Community(models.Model):
    name = models.CharField("Community name", max_length=255)
    members = models.TextField(blank=True, null=True,
                               help_text="A list of members separated by newlines. (\\n)")

    @property
    def member_list(self):
        return "\n".join(self.members)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Communities"
