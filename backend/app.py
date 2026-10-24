from fastapi import FastAPI

try:
    from backend.security import AuthTokenMiddleware
except ImportError:
    from security import AuthTokenMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Enrwine API", version="1.0")
    app.add_middleware(AuthTokenMiddleware)
    return app
