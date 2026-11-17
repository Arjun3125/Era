"""LLM error types shared by runtimes and callers."""


class QuotaExhaustedError(RuntimeError):
    """Free-tier LLM quota is exhausted.

    Callers must not degrade silently: completed LLM calls stay in the response
    cache, failed turns are queued, and a later retry continues from the last
    unfinished call instead of paying for the finished work again.
    """
