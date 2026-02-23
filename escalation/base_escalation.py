"""Abstract escalation contract."""

from abc import ABC, abstractmethod


class BaseEscalation(ABC):
    """Contract for escalation handlers.

    An escalation executes any side effects (e.g. posting to Discord, sending
    an email) and returns a plain-English result string. That string is passed
    directly back to the model as the tool result, so it should convey whether
    the escalation succeeded and any relevant details the model can relay to
    the user.
    """

    @abstractmethod
    def escalate(self, user_message: str) -> str:
        """Execute the escalation and return a result string for the model.

        Side effects (webhook calls, notifications, etc.) happen here.

        The return value is passed back to the LLM as the tool result and must
        be human-readable. It should contain enough info for the model to craft
        a reassuring reply: a success confirmation, or a failure notice so the
        model can apologise and suggest the user find an organizer directly.
        """
        ...
