from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, pokemon

app = FastAPI(
    title="PokéAPI Local",
    description="API que expone los datos guardados por el CLI de Pokémon.",
    version="1.0.0",
)

# Middleware de CORS (debe ir antes de include_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pokemon.router)


@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a la PokéAPI Local. "
        "Ve a /docs para ver la documentación."
    }


app.include_router(auth.router)
