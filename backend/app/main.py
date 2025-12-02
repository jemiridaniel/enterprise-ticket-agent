from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import health, tickets

app = FastAPI(title="Enterprise Ticket Agent")

# --- CORS ---
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(tickets.router)


@app.get("/")
async def root():
    return {"message": "Enterprise Ticket Agent backend is running"}
