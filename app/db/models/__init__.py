"""Import every ORM model so SQLAlchemy's mapper registry is fully populated.

Anything that needs ``Base.metadata`` (Alembic autogenerate, ``create_all``
in tests) must import this module rather than an individual model module.
"""

from app.db.base import Base
from app.db.models.agent_run import AgentRun, ToolCall
from app.db.models.approval import Approval
from app.db.models.browser_session import BrowserSession
from app.db.models.draft import Draft
from app.db.models.research import ResearchClaim, ResearchSource
from app.db.models.social_post import PublishAttempt, SocialPost
from app.db.models.task import Task, TaskStep
from app.db.models.user import User
from app.db.models.verification import ErrorLog, VerificationResult

__all__ = [
    "Base",
    "User",
    "Task",
    "TaskStep",
    "AgentRun",
    "ToolCall",
    "Approval",
    "BrowserSession",
    "ResearchSource",
    "ResearchClaim",
    "Draft",
    "SocialPost",
    "PublishAttempt",
    "VerificationResult",
    "ErrorLog",
]
