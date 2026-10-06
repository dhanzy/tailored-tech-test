from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from cache_service import service
from cache_service.config import ServiceSettings
from cache_service.schemas import PayloadCreated, PayloadRequest, PayloadResponse
from cache_service.transformer import Transformer, upper_transformer


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def get_transformer() -> Transformer:
    # A dependency so tests can swap in a call-counting fake.
    return upper_transformer


SessionDep = Annotated[Session, Depends(get_session)]
TransformerDep = Annotated[Transformer, Depends(get_transformer)]


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    settings = settings or ServiceSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine: Engine = create_engine(
            settings.sqlalchemy_url,
            # Sync endpoints run in a threadpool; SQLite must allow cross-thread use.
            connect_args=(
                {"check_same_thread": False} if settings.sqlalchemy_url.startswith("sqlite") else {}
            ),
        )
        SQLModel.metadata.create_all(engine)
        app.state.engine = engine
        yield
        engine.dispose()

    app = FastAPI(title="Caching service", lifespan=lifespan)

    # Plain `def` endpoints: DB and transformer calls are blocking, so FastAPI
    # should run them in its threadpool rather than on the event loop.
    @app.post("/payload", status_code=status.HTTP_201_CREATED, response_model=PayloadCreated)
    def create_payload(
        body: PayloadRequest,
        session: SessionDep,
        transform: TransformerDep,
    ) -> PayloadCreated:
        pid = service.create_payload(session, body, transform)
        return PayloadCreated(id=pid, message="Payload created")

    @app.get("/payload/{payload_id}", response_model=PayloadResponse)
    def read_payload(payload_id: str, session: SessionDep) -> PayloadResponse:
        output = service.read_payload(session, payload_id)
        if output is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Payload not found")
        return PayloadResponse(output=output)

    return app
