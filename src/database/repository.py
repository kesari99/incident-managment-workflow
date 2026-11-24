

from database.models import Incident
from sqlalchemy.ext.asyncio import AsyncSession


class IncidentRepository:
    def __init__(self, session:AsyncSession):
        self.session= session
    async def create(
        self,
        title:str,
        description:str,
        service:str,
        reported_by:str,
        external_id:str,
        ) -> Incident:

        incident = Incident(
             title=title,
            description=description,
            service=service,
            reported_by=reported_by,
            external_id=external_id,
        )

        self.session.add(incident)
        await self.session.flush()
        await self.session.refresh(incident)
        return incident

        

class WorkFlowRunRepository:
    def __init__(self) -> None:
        

class EventRepository:
    def __init__(self) -> None:
        pass


class ApprovalRepository:
    def __init__(self) -> None:
        pass