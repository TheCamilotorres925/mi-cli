from fastapi import FastAPI

from .routers import pokemon

app = FastAPI(
    title="PokéAPI Local",
    description="API que expone los datos guardados por el CLI de Pokémon.",
    version="1.0.0",
)

# Conectamos el router
app.include_router(pokemon.router)


@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a la PokéAPI Local. "
        "Ve a /docs para ver la documentación."
    }
