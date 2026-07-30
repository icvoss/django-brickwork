from __future__ import annotations

from django.db import models


class Widget(models.Model):
    """A trivial CRUD subject for the shell/nav/table/form harness."""

    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
