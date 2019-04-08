from django.db import models


class Community(models.Model):
    name = models.CharField("Community name", max_length=255)
    members = models.TextField(blank=True, null=True,
                               help_text="A list of members separated by newlines. (\\n)")

    @property
    def member_list(self):
        """Split the member_list with newline char. and return a Python list."""

        if self.members:
            members = self.members.split("\n")
            members = map(lambda x: x.strip(), members)
            return list(members)
        else:
            return []

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Communities"
