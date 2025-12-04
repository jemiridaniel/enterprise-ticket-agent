from typing import List
from fastapi import APIRouter, HTTPException

from ..models.tickets import (
    TicketCreateRequest,
    TicketResponse,
    TicketHistoryItem,
    TicketThreadResponse,
    FollowupRequest,
)

from ..services.agent_orchestrator import (
    handle_ticket,
    list_ticket_history,
    get_ticket_thread,
    handle_followup,
)

from ..services.vector_service import vector_store


# -------------------------------------------------
# Correct router (defined ONCE)
# -------------------------------------------------

router = APIRouter(prefix="/tickets", tags=["tickets"])


# -------------------------------------------------
# Create Ticket  (POST /tickets)
# -------------------------------------------------

@router.post("/", response_model=TicketResponse)
async def create_ticket(req: TicketCreateRequest) -> TicketResponse:
    try:
        return await handle_ticket(req)
    except Exception as e:
        import traceback
        print("🔥 ERROR IN create_ticket()")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Ticket History  (GET /tickets)
# -------------------------------------------------

@router.get("/", response_model=List[TicketHistoryItem])
async def get_ticket_history(limit: int = 50) -> List[TicketHistoryItem]:
    try:
        return await list_ticket_history(limit=limit)
    except Exception as e:
        import traceback
        print("🔥 ERROR IN get_ticket_history()")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Load Thread (GET /tickets/{ticket_id}/thread)
# -------------------------------------------------

@router.get("/{ticket_id}/thread", response_model=TicketThreadResponse)
async def get_thread(ticket_id: str) -> TicketThreadResponse:
    try:
        thread = await get_ticket_thread(ticket_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return thread
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("🔥 ERROR IN get_thread()")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Follow-up (POST /tickets/{ticket_id}/followup)
# -------------------------------------------------

@router.post("/{ticket_id}/followup", response_model=TicketThreadResponse)
async def post_followup(ticket_id: str, body: FollowupRequest) -> TicketThreadResponse:
    try:
        return await handle_followup(ticket_id, body.message)
    except Exception as e:
        import traceback
        print("🔥 ERROR IN post_followup()")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Close Ticket (POST /tickets/{ticket_id}/close)
# -------------------------------------------------

@router.post("/{ticket_id}/close")
async def close_ticket_route(ticket_id: str):
    try:
        vector_store.close_ticket(ticket_id)
        return {"ticket_id": ticket_id, "status": "closed"}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        print("🔥 ERROR IN close_ticket_route()")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
