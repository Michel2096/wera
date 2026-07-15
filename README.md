# Health Monitor API

API REST profesional para una aplicación de monitoreo de salud, inspirada en Huawei Health. Construida con **Flask + Flask-SocketIO + MongoDB Atlas**, con **autenticación por sesiones seguras de servidor (sin JWT)**, documentación **Swagger/OpenAPI**, y **sincronización en tiempo real** de métricas biométricas simuladas.

---

## 1. Características principales

- **Autenticación por sesiones**, no por tokens: `Flask-Session` persiste las sesiones directamente en MongoDB Atlas (colección `sessions`), con cookie `HttpOnly` firmada por el servidor.
- **Arquitectura modular** de nivel empresarial: `models/`, `routes/`, `services/`, `sockets/`, `utils/`, `database/`, separando responsabilidades con claridad.
- **Datos biométricos simulados** (no hay sensores reales): cada usuario conectado por WebSocket recibe una nueva lectura cada 3 segundos (configurable), generada y persistida automáticamente.
- **Aislamiento estricto por usuario**: todo registro (dispositivo, métrica, log) incluye `user_id`, y toda consulta filtra por ese campo — un usuario nunca puede ver datos de otra cuenta.
- **WebSockets en tiempo real** vía `Flask-SocketIO`, usando *rooms* privadas por usuario para la emisión de datos.
- **Vinculación de dispositivos por código QR**: genera un token temporal único, lo codifica en un QR (PNG en base64), y permite que un reloj inteligente lo redima sin necesidad de sesión de navegador.
- **Swagger/OpenAPI** interactivo en `/docs/`, generado con `Flasgger` a partir de docstrings YAML en cada endpoint.
- **Manejo global de errores**, validación de payloads, logging estructurado (consola + archivo rotativo) y auditoría de actividad (`activity_logs`).
- **Accesible desde la red local**: al escuchar en `0.0.0.0`, cualquier dispositivo en la misma red WiFi (teléfono, reloj, Expo Go) puede consumir la API usando la IP local del servidor.
- **Docker y Docker Compose** listos para producción.
- **Pruebas unitarias** con `pytest` + `mongomock` (20 pruebas, capa de servicios).

---

## 2. Estructura del proyecto

```
health_monitor_api/
├── app.py                     # Application factory + arranque de SocketIO y simulador
├── config.py                  # Configuración por entorno (dev/prod/test)
├── requirements.txt
├── .env.example                # Plantilla de variables de entorno
├── Dockerfile
├── docker-compose.yml
├── database/
│   └── mongo.py                # Conexión a MongoDB Atlas + índices
├── models/                     # Construcción y serialización de documentos
│   ├── user.py
│   ├── device.py
│   ├── health_metric.py
│   ├── session_model.py
│   └── activity_log.py
├── routes/                     # Blueprints (capa HTTP + Swagger docstrings)
│   ├── auth_routes.py
│   ├── profile_routes.py
│   ├── health_routes.py
│   ├── device_routes.py
│   └── dashboard_routes.py
├── services/                   # Lógica de negocio
│   ├── auth_service.py
│   ├── user_service.py
│   ├── device_service.py
│   ├── health_service.py
│   ├── qr_service.py
│   └── simulator_service.py
├── sockets/
│   └── health_socket.py        # Eventos de Socket.IO (connect/disconnect)
├── utils/
│   ├── validators.py
│   ├── error_handlers.py
│   ├── decorators.py           # @login_required
│   ├── logger.py
│   └── responses.py
└── tests/
    ├── conftest.py              # Fixtures (mongomock, sesión simulada)
    ├── test_auth.py
    ├── test_health.py
    └── test_device.py
```

---

## 3. Colecciones de MongoDB Atlas

| Colección | Campos | Notas |
|---|---|---|
| `users` | `_id, name, email, password_hash, birth_date, gender, weight, height, created_at` | `email` con índice único. Contraseña con `bcrypt`. |
| `devices` | `_id, user_id, device_name, device_type, status, qr_token, created_at` | `status`: `pending` \| `connected` \| `disconnected`. Índices por `user_id` y `qr_token`. |
| `health_metrics` | `_id, user_id, heart_rate, oxygen, steps, calories, distance, sleep, stress, temperature, created_at` | Índice compuesto `(user_id, created_at)` para historial rápido. |
| `sessions` | `_id, user_id, session_id, created_at` | Administrada por `Flask-Session`; índice TTL sobre `expires_at`. |
| `activity_logs` | `_id, user_id, action, timestamp` | Auditoría: login, logout, registro, conexión de dispositivos, etc. |

---

## 4. Autenticación por sesiones (sin JWT)

1. `POST /auth/login` valida credenciales con `bcrypt` y guarda `user_id` en `flask.session`.
2. `Flask-Session` serializa esa sesión como un documento en la colección `sessions` de MongoDB Atlas, y entrega al cliente una cookie `HttpOnly` firmada (`health_monitor_session`) que solo contiene un identificador de sesión opaco — nunca datos ni tokens.
3. En cada request posterior, Flask recupera automáticamente la sesión desde MongoDB usando esa cookie.
4. Las rutas protegidas usan el decorador `@login_required` (`utils/decorators.py`), que verifica `session.get("user_id")`.
5. Los eventos de WebSocket reutilizan la **misma cookie de sesión** (`manage_session=True` en Flask-SocketIO), por lo que no se requiere ningún token adicional para el canal en tiempo real.
6. `POST /auth/logout` limpia la sesión de servidor.

Esto satisface el requisito de **sesiones seguras de servidor con almacenamiento persistente en MongoDB Atlas**, sin usar JWT.

---

## 5. Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/register` | No | Registrar usuario nuevo |
| POST | `/auth/login` | No | Iniciar sesión (crea cookie de sesión) |
| POST | `/auth/logout` | Sí | Cerrar sesión |
| GET | `/auth/session` | Sí | Consultar el estado de la sesión actual |
| GET | `/profile` | Sí | Obtener perfil del usuario |
| PUT | `/profile` | Sí | Actualizar perfil |
| GET | `/health/current` | Sí | Última métrica biométrica |
| GET | `/health/history` | Sí | Historial paginado (`?page=&limit=`) |
| GET | `/health/statistics` | Sí | Estadísticas agregadas |
| POST | `/device/connect` | Depende* | Conectar dispositivo (directo o vía QR) |
| GET | `/device/list` | Sí | Listar dispositivos del usuario |
| POST | `/device/disconnect` | Sí | Desconectar un dispositivo |
| GET | `/device/qr` | Sí | Generar QR temporal de vinculación |
| GET | `/dashboard` | Sí | Resumen consolidado (perfil + dispositivos + métrica + estadísticas) |

\* `POST /device/connect` **no requiere sesión** cuando el body incluye `qr_token` (flujo del reloj inteligente escaneando el QR). Si no se envía `qr_token`, sí requiere sesión activa (conexión directa, p. ej. la propia app del usuario).

Documentación interactiva completa (probar cada endpoint desde el navegador): **`/docs/`**
Especificación OpenAPI cruda: **`/apispec.json`**

---

## 6. Flujo de vinculación de dispositivos por QR

```
Usuario (app, con sesión)                 Servidor                          Reloj inteligente
       |--- GET /device/qr -------------->|
       |                                  |  genera qr_token + doc "pending"
       |<---- { qr_token, imagen QR } ----|
       | (muestra el QR en pantalla)      |
       |                                              (escanea el QR)
       |                                  |<--- POST /device/connect {qr_token,...} ---|
       |                                  |  valida token, no expiró           |
       |                                  |  marca device -> "connected"       |
       |                                  |----- 201 dispositivo conectado --->|
```

El token expira en `QR_TOKEN_EXPIRATION_SECONDS` (por defecto 120s). Si expira o ya fue usado, `POST /device/connect` responde `404`/`409`.

---

## 7. Sincronización en tiempo real (WebSockets)

- Evento `connect`: valida la sesión (misma cookie que la API REST), une al usuario a una *room* privada (`user_id`) y comienza a recibir datos.
- Cada `SIMULATION_INTERVAL_SECONDS` (por defecto 3s), el servidor genera una lectura biométrica simulada por cada usuario conectado, la guarda en `health_metrics` y la emite **solo a su room** mediante el evento `health_update`.
- Evento `disconnect`: remueve al usuario de la lista de conexiones activas.

Ejemplo de cliente (JavaScript / React Native con `socket.io-client`):

```javascript
import { io } from "socket.io-client";

const socket = io("http://<IP_LOCAL_DEL_SERVIDOR>:5000", {
  withCredentials: true, // envía la cookie de sesión
});

socket.on("connection_ack", (data) => console.log("Conectado:", data));
socket.on("health_update", (payload) => console.log("Nueva métrica:", payload.data));
socket.on("connection_error", (err) => console.error(err));
```

> Importante: el cliente debe haber iniciado sesión previamente vía `POST /auth/login` (mismo dominio/cookie) para que el WebSocket lo autentique.

---

## 8. Acceso desde la red local (teléfonos y relojes)

El servidor escucha en `HOST=0.0.0.0`, por lo que es accesible desde cualquier dispositivo conectado a la misma red WiFi usando la IP local de la máquina que ejecuta la API:

```bash
# En Linux/macOS
ifconfig | grep "inet "
# En Windows
ipconfig
```

Luego, desde el teléfono / reloj / Expo Go, apunta a `http://<IP_LOCAL>:5000`.

---

## 9. Instalación y ejecución local

```bash
# 1. Clonar/copiar el proyecto y entrar a la carpeta
cd health_monitor_api

# 2. Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env y coloca tu MONGO_URI real de MongoDB Atlas

# 5. Ejecutar
python app.py
```

La API quedará disponible en `http://0.0.0.0:5000`, con Swagger en `http://localhost:5000/docs/`.

---

## 10. Ejecución con Docker

```bash
cp .env.example .env
# Completa MONGO_URI con tu cadena de conexión de Atlas

docker compose up --build
```

---

## 11. Pruebas unitarias

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Las pruebas usan `mongomock` para simular MongoDB Atlas, por lo que **no requieren conexión real a internet ni credenciales**. Cubren:

- Registro/login/logout y manejo de contraseñas con `bcrypt`.
- Aislamiento de métricas biométricas entre distintos usuarios.
- Paginación y estadísticas agregadas.
- Conexión/desconexión de dispositivos y su aislamiento por usuario.
- Generación y redención de tokens QR (incluyendo expiración y reutilización).

---

## 12. Configuración de MongoDB Atlas (paso a paso)

1. Crea un clúster gratuito en [MongoDB Atlas](https://www.mongodb.com/atlas).
2. En **Database Access**, crea un usuario con permisos de lectura/escritura.
3. En **Network Access**, agrega tu IP (o `0.0.0.0/0` solo para desarrollo).
4. En **Database > Connect > Drivers**, copia la cadena de conexión (`mongodb+srv://...`).
5. Pégala en tu archivo `.env` como `MONGO_URI`, reemplazando usuario/contraseña.
6. Al arrancar la app, `database/mongo.py` valida la conexión con `ping` y crea automáticamente todos los índices necesarios.

---

## 13. Notas de seguridad

- Las contraseñas nunca se almacenan en texto plano: se usa `bcrypt` con `BCRYPT_ROUNDS` configurable.
- Las cookies de sesión son `HttpOnly`; en producción, activa `SESSION_COOKIE_SECURE=True` (requiere HTTPS).
- CORS está configurado vía `CORS_ORIGINS`; en producción, restringe a los orígenes reales de tu app en vez de `*`.
- Cada consulta a `health_metrics`, `devices` y `activity_logs` filtra explícitamente por `user_id`, evitando fugas de datos entre cuentas.
