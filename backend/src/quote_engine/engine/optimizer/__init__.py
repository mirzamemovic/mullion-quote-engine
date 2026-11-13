"""Cutting optimizer: lay the demanded pieces onto stock bars (PLAN.md section 4.4).

Capacity rule, the same for every method: ``usable = bar_length - bar_end_trim``; each piece uses
``length + kerf``; a bar is valid when the sum of those is at most ``usable``.
"""
