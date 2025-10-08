"""Complete FastAPI server for SevenTech automation platform with interactive mapping support."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from uuid_extensions import uuid7str

from browser_use.llm.google.chat import ChatGoogle

from seventech.api.session_manager import MappingSessionState, SessionManager
from seventech.executor.service import Executor
from seventech.executor.views import ExecutePlanRequest, ExecutorConfig
from seventech.mapper.interactive import InteractiveMapper
from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.planner.service import Planner
from seventech.shared_views import ExecutionResult, Plan
from seventech.storage.service import Storage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

tags_dict: Dict[str, Optional[List[Union[str, Enum]]]] = {
    "mapping": ["Mapping"],
    "plans": ["Plans"],
    "execution": ["Execution"],
    "auth": ["Authentication"],
}
# Global service instances
storage: Storage | None = None
planner: Planner | None = None
executor: Executor | None = None
session_manager: SessionManager | None = None
interactive_mapper: InteractiveMapper | None = None


# ==================== REQUEST/RESPONSE MODELS ====================


class StartMappingRequest(BaseModel):
    """Request to start an interactive mapping session."""

    objective: str = Field(description="Natural language description of the objective")
    starting_url: str | None = Field(default=None, description="Optional starting URL")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    plan_name: str | None = Field(
        default=None, description="Optional name for the plan"
    )


class ProvideInputRequest(BaseModel):
    """Request to provide input for a pending request."""

    value: str = Field(description="User-provided value")


class CreatePlanRequest(BaseModel):
    """Request to create a plan from a completed mapping session."""

    session_id: str = Field(description="ID of the completed mapping session")
    plan_name: str | None = Field(default=None, description="Optional plan name")


class AuthRequest(BaseModel):
    """Request to create a plan from a completed mapping session."""

    token: str = Field(description="Token for authentication")


# ==================== LIFECYCLE ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the API."""
    global storage, planner, executor, session_manager, interactive_mapper

    logger.info("🚀 Initializing SevenTech API services...")

    # Initialize core services
    storage = Storage()
    planner = Planner()
    executor = Executor(ExecutorConfig(headless=True))
    session_manager = SessionManager()

    # Initialize interactive mapper with LLM
    try:
        llm = ChatGoogle(model="gemini-2.5-flash")
        interactive_mapper = InteractiveMapper(
            llm=llm, config=MapperConfig(headless=False)
        )
        logger.info("✅ InteractiveMapper initialized with Gemini")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize InteractiveMapper: {e}")
        interactive_mapper = None

    logger.info("✅ SevenTech API ready")

    yield

    logger.info("🛑 Shutting down SevenTech API...")


# Create FastAPI app
app = FastAPI(
    title="SevenTech Automation API",
    description="Complete API for AI-powered browser automation with interactive mapping",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HEALTH CHECK ====================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "SevenTech Automation API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "interactive_mapping": interactive_mapper is not None,
            "execution": executor is not None,
            "storage": storage is not None,
        },
    }


# ==================== INTERACTIVE MAPPING ENDPOINTS ====================

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

security = HTTPBearer(auto_error=False)


async def validate_api_key(token: str = Depends(security)) -> bool:
    """Validate API key if authentication is enabled."""
    # For development, allow access without token
    # In production, implement proper API key validation
    return True


@app.get(
    "/api/v1/auth",
    response_model=dict[str, Any],
    tags=tags_dict["auth"],
)
async def auth():
    """Authenticate user."""
    return {"status": "authenticated", "message": "Authentication successful"}


@app.post(
    "/api/v1/mapping/start",
    response_model=dict[str, Any],
    tags=tags_dict["mapping"],
)
async def start_mapping(request: StartMappingRequest):
    """Start an interactive mapping session.

    This endpoint starts a background task that runs the mapper.
    The mapper will pause when it needs user input, which can be
    provided via the /mapping/sessions/{session_id}/input endpoint.

    Use SSE endpoint /mapping/sessions/{session_id}/events to get
    real-time notifications.
    """
    if not interactive_mapper or not session_manager:
        raise HTTPException(status_code=503, detail="Interactive mapping not available")

    # Create session
    session_id = uuid7str()
    session = session_manager.create_session(session_id, request.objective)

    # Create mapping request
    map_request = MapObjectiveRequest(
        objective=request.objective,
        starting_url=request.starting_url,
        tags=request.tags,
        plan_name=request.plan_name,
    )

    # Start mapping in background
    async def run_mapper():
        """Background task to run interactive mapper."""
        assert session_manager is not None
        assert interactive_mapper is not None

        logger.info(f"Starting mapper for session {session_id}")

        # Setup input callback to use session manager
        async def handle_input_async(input_request):
            """Handle input request through session manager."""
            assert session_manager is not None
            return await session_manager.request_input(session_id, input_request)

        # Set the session's input callback
        session.on_input_needed = handle_input_async

        try:
            # Run mapper with existing session
            mapper_result, _ = await interactive_mapper.map_objective(
                map_request, session=session
            )
            session_manager.store_result(session_id, mapper_result)

            logger.info(f"Session {session_id} completed: {mapper_result.success}")

        except Exception as e:
            logger.error(f"Session {session_id} failed: {e}", exc_info=True)
            session.fail(str(e))

    # Start background task
    asyncio.create_task(run_mapper())

    logger.info(f"Mapping session started: {session_id}")

    return {
        "session_id": session_id,
        "status": "started",
        "message": "Mapping session started. Use SSE endpoint for real-time updates.",
        "sse_url": f"/api/v1/mapping/sessions/{session_id}/events",
        "status_url": f"/api/v1/mapping/sessions/{session_id}",
    }


@app.get(
    "/api/v1/mapping/sessions/{session_id}",
    response_model=MappingSessionState,
    tags=tags_dict["mapping"],
)
async def get_mapping_session(session_id: str):
    """Get the current state of a mapping session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    state = session_manager.get_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return state


@app.post(
    "/api/v1/mapping/sessions/{session_id}/input",
    tags=tags_dict["mapping"],
)
async def provide_input(session_id: str, request: ProvideInputRequest):
    """Provide user input for a pending input request.

    When a mapping session is waiting for input (status: WAITING_FOR_INPUT),
    use this endpoint to provide the required value.
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # Provide input
    success = session_manager.provide_input(session_id, request.value)

    if not success:
        raise HTTPException(
            status_code=400, detail="No pending input request for this session"
        )

    return {"status": "accepted", "message": "Input provided, session will continue"}


@app.get(
    "/api/v1/mapping/sessions/{session_id}/events",
    tags=tags_dict["mapping"],
)
async def session_events(session_id: str):
    """Server-Sent Events stream for real-time session updates.

    Subscribe to this endpoint to get notifications when:
    - Session status changes
    - Input is needed
    - Mapping completes or fails
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    async def event_generator():
        """Generate SSE events."""
        assert session_manager is not None

        last_status = session.status

        while True:
            # Send current status
            state = session_manager.get_session_state(session_id)
            if state:
                # Status change event
                if state.status != last_status:
                    yield f"event: status_change\ndata: {state.model_dump_json()}\n\n"
                    last_status = state.status

                # Input needed event
                if state.current_input_request:
                    yield f"event: input_needed\ndata: {state.model_dump_json()}\n\n"

                # Completed/failed events
                if state.status in ["completed", "failed", "cancelled"]:
                    yield f"event: {state.status}\ndata: {state.model_dump_json()}\n\n"
                    break

            # Wait before next check
            await asyncio.sleep(1)

        # Final message
        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post(
    "/api/v1/mapping/sessions/{session_id}/cancel",
    tags=tags_dict["mapping"],
)
async def cancel_mapping(session_id: str):
    """Cancel a running mapping session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    success = session_manager.cancel_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {"status": "cancelled", "session_id": session_id}


@app.get(
    "/api/v1/mapping/sessions",
    tags=tags_dict["mapping"],
)
async def list_mapping_sessions():
    """List all active mapping sessions."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    sessions = session_manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@app.delete(
    "/api/v1/mapping/sessions/{session_id}",
    tags=tags_dict["mapping"],
)
async def delete_mapping_session(session_id: str):
    """Delete a mapping session and clean up resources."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")

    success = session_manager.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {"status": "deleted", "session_id": session_id}


# ==================== PLAN CREATION FROM MAPPING ====================


@app.post(
    "/api/v1/mapping/sessions/{session_id}/create-plan",
    response_model=Plan,
    tags=tags_dict["mapping"],
)
async def create_plan_from_session(session_id: str, plan_name: str | None = None):
    """Create a plan from a completed mapping session.

    After a mapping session completes, use this endpoint to convert
    the collected actions into an executable plan.
    """
    if not session_manager or not planner or not storage:
        raise HTTPException(status_code=503, detail="Required services not available")

    # Get mapper result
    mapper_result = session_manager.get_result(session_id)
    if not mapper_result:
        raise HTTPException(
            status_code=404, detail=f"No result found for session: {session_id}"
        )

    if not mapper_result.success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create plan from failed mapping: {mapper_result.error_message}",
        )

    # Create plan
    plan = planner.create_plan(mapper_result, plan_name)

    # Save plan
    storage.save_plan(plan)

    logger.info(f"Plan created from session {session_id}: {plan.metadata.plan_id}")

    return plan


# ==================== PLAN MANAGEMENT ENDPOINTS ====================


@app.get(
    "/api/v1/plans",
    response_model=list[Plan],
    tags=tags_dict["plans"],
)
async def list_plans(tags: str | None = None):
    """List all available plans."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    plans = storage.list_plans(tags=tag_list)
    return plans


@app.get(
    "/api/v1/plans/search",
    response_model=list[Plan],
    tags=tags_dict["plans"],
)
async def search_plans(query: str):
    """Search plans by name or description."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    plans = storage.search_plans(query)
    return plans


@app.get("/api/v1/plans/{plan_id}", response_model=Plan, tags=tags_dict["plans"])
async def get_plan(plan_id: str):
    """Get a specific plan by ID."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        plan = storage.load_plan(plan_id)
        return plan
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")


@app.delete("/api/v1/plans/{plan_id}", tags=tags_dict["plans"])
async def delete_plan(plan_id: str):
    """Delete a plan."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    success = storage.delete_plan(plan_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    return {"status": "deleted", "plan_id": plan_id}


# ==================== EXECUTION ENDPOINTS ====================


@app.post(
    "/api/v1/execute/{plan_id}",
    response_model=ExecutionResult,
    tags=tags_dict["execution"],
)
async def execute_plan(plan_id: str, params: dict[str, Any] | None = None):
    """Execute a plan with provided parameters.

    This is the main endpoint for running automation tasks.
    NO LLM is used - execution is completely deterministic.

    Example:
            POST /api/v1/execute/abc123
            {
                    "inscricao_imobiliaria": "1234567890",
                    "cpf": "123.456.789-00"
            }
    """
    if not executor or not storage:
        raise HTTPException(status_code=503, detail="Required services not available")

    try:
        # Load plan
        plan = storage.load_plan(plan_id)

        # Create execution request
        request = ExecutePlanRequest(plan_id=plan_id, params=params or {})

        # Execute plan
        result = await executor.execute_plan(plan, request)

        # Save result
        storage.save_execution_result(result)

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    except Exception as e:
        logger.error(f"Error executing plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/executions",
    response_model=list[ExecutionResult],
    tags=tags_dict["execution"],
)
async def list_executions(plan_id: str | None = None):
    """List execution results, optionally filtered by plan ID."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    results = storage.list_execution_results(plan_id=plan_id)
    return results


@app.get(
    "/api/v1/executions/{execution_id}",
    response_model=ExecutionResult,
    tags=tags_dict["execution"],
)
async def get_execution(execution_id: str):
    """Get a specific execution result by ID."""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        result = storage.load_execution_result(execution_id)
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Execution not found: {execution_id}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
