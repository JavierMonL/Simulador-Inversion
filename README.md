# Simulador de Inversión VaZentica V1.3 — Acceso Google

## Archivos
- `app.py`: simulador + control de acceso.
- `Logo Capital.png`: logo usado en el PDF.
- `requirements.txt`: dependencias, incluida Authlib.
- `.streamlit/secrets.toml.example`: plantilla de configuración.
- `.gitignore`: evita subir el secreto real.

## Prueba local
1. Copia `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml`.
2. En Google Cloud, usa el Client ID y Client Secret del cliente `Simulador Inversiones`.
3. Sustituye los placeholders del archivo `secrets.toml`.
4. Genera un `cookie_secret` largo y aleatorio.
5. Mantén para local:
   `redirect_uri = "http://localhost:8501/oauth2callback"`
6. Ejecuta:
   `python -m streamlit run app.py`

## Producción
En Streamlit Community Cloud NO subas `secrets.toml`.
Pega su contenido en la sección Secrets de la app y cambia `redirect_uri` a la URL pública exacta terminada en `/oauth2callback`.
Agrega esa misma URI en Google Auth Platform > Simulador Inversiones > URIs de redireccionamiento autorizados.

## Acceso
Los correos autorizados están en `[acceso].usuarios` dentro de Secrets.
