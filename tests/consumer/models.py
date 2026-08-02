from __future__ import annotations

from django.db import models


class Ticket(models.Model):
    """A trivial tenant-scoped subject for the 422 form loop and the data
    table on the shipped-surface page. Not a real tenancy implementation
    (that is the host application's job); tenant scoping here is just a
    plain CharField so the fixture stays a plain Django app."""

    tenant_slug = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    priority = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("normal", "Normal"), ("urgent", "Urgent")],
        default="normal",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title
