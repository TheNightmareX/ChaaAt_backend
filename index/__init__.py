"""Monkey patches.
"""
from django.db.models.sql import datastructures
from django.core.exceptions import EmptyResultSet

# Use `setattr` to bypass the type checking.
setattr(datastructures, 'EmptyResultSet', EmptyResultSet)
