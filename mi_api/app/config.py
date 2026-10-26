import os


class Settings:
    def __init__(self):
        # Lee la variable de entorno API_KEY.
        # Si no existe, lanza una excepción para evitar arrancar sin seguridad.
        self.API_KEY = os.getenv("API_KEY")
        if not self.API_KEY:
            raise ValueError(
                "¡Falta la variable de entorno API_KEY! "
                "Configúrala antes de arrancar el servidor."
            )


# Instancia global de configuración
settings = Settings()
