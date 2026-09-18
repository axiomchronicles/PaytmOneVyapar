from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AgentRun, AgentSession


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def session_by_thread(self, thread_id: str) -> AgentSession | None:
        return await self.session.scalar(
            select(AgentSession).where(AgentSession.thread_id == thread_id)
        )

    async def add_run(self, run: AgentRun) -> AgentRun:
        self.session.add(run)
        await self.session.flush()
        return run
