# Freelancer Management System - Backend

Sistema todo-en-uno minimalista para freelancers (desarrolladores, diseñadores, consultores) que unifica tareas, registro de tiempo y facturación.

## 🚀 Características

- **Gestión de Clientes y Proyectos**: CRUD completo con soporte multi-moneda
- **Sistema de Tareas**: Kanban simple con estados personalizables
- **Time Tracking**: Cronómetro por tarea/proyecto con edición manual
- **Facturación**: Generación de PDFs en 1 clic desde horas registradas
- **Compartir**: Links públicos para proyectos, hojas de tiempo y facturas
- **Multi-usuario**: Sistema de roles por proyecto (owner, contributor, viewer)

## 🏗️ Arquitectura

- **Framework**: FastAPI con arquitectura hexagonal (Domain-Driven Design)
- **Base de Datos**: PostgreSQL a través de Supabase
- **Autenticación**: Supabase Auth con JWT
- **Storage**: Supabase Storage para PDFs y archivos
- **Seguridad**: Row Level Security (RLS) en todas las tablas

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 14+ (o cuenta en Supabase)
- Redis (opcional, para caché y rate limiting)
- Docker y Docker Compose (opcional, para desarrollo)

## 🔧 Instalación

### Opción 1: Setup Automático

```bash
# Dar permisos de ejecución al script
chmod +x setup.sh

# Ejecutar el script de setup
./setup.sh
```

### Opción 2: Setup Manual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Copiar archivo de configuración
cp .env.example .env

# Editar .env con tus credenciales de Supabase
```

## ⚙️ Configuración

### 1. Configurar Supabase

1. Crear una cuenta en [Supabase](https://supabase.com)
2. Crear un nuevo proyecto
3. Obtener las credenciales:
   - `SUPABASE_URL`: URL del proyecto
   - `SUPABASE_ANON_KEY`: Anonymous/Public key
   - `SUPABASE_SERVICE_KEY`: Service role key

### 2. Actualizar .env

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
SUPABASE_SERVICE_KEY=tu-service-key
JWT_SECRET_KEY=genera-una-clave-secreta-segura
DATABASE_URL=postgresql://...  # Opcional, para migraciones directas
```

### 3. Ejecutar Migraciones

```bash
# Con Alembic
alembic upgrade head

# O con Make
make migrate
```

## 🚀 Ejecución

### Desarrollo Local

```bash
# Con uvicorn directamente
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# O con Make
make run
```

### Con Docker

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f app

# Detener servicios
docker-compose down
```

## 📚 Documentación API

Una vez ejecutando, la documentación está disponible en:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=app --cov-report=html

# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration

# Con Make
make test
```

## 📁 Estructura del Proyecto

```
app/
├── domain/           # Capa de dominio (modelos, servicios, interfaces)
│   ├── models/       # Entidades del dominio
│   ├── services/     # Servicios de dominio
│   └── repositories/ # Interfaces de repositorios
├── application/      # Capa de aplicación
│   ├── use_cases/    # Casos de uso
│   └── dto/          # Data Transfer Objects
├── infrastructure/   # Capa de infraestructura
│   ├── db/          # Configuración de base de datos
│   ├── repositories/ # Implementación de repositorios
│   ├── auth/        # Autenticación y autorización
│   ├── pdf/         # Generación de PDFs
│   ├── storage/     # Almacenamiento de archivos
│   └── web/         # Capa web (routers, middleware)
├── config.py        # Configuración de la aplicación
└── main.py          # Punto de entrada
```

## 🛠️ Comandos Útiles (Makefile)

```bash
make help        # Ver todos los comandos disponibles
make install     # Instalar dependencias
make run         # Ejecutar aplicación
make test        # Ejecutar tests
make lint        # Ejecutar linters
make format      # Formatear código
make clean       # Limpiar archivos temporales
make docker-up   # Iniciar servicios Docker
make docker-down # Detener servicios Docker
make migrate     # Ejecutar migraciones
```

## 🔒 Seguridad

- **RLS (Row Level Security)**: Habilitado en todas las tablas
- **JWT**: Tokens con expiración configurable
- **CORS**: Configuración restrictiva para producción
- **Rate Limiting**: Límites por endpoint
- **Validación**: Estricta validación de inputs con Pydantic

## 📝 Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `SUPABASE_URL` | URL del proyecto Supabase | ✅ |
| `SUPABASE_ANON_KEY` | Anonymous key de Supabase | ✅ |
| `SUPABASE_SERVICE_KEY` | Service role key de Supabase | ✅ |
| `JWT_SECRET_KEY` | Clave secreta para JWT | ✅ |
| `DATABASE_URL` | URL directa a PostgreSQL | ❌ |
| `ENVIRONMENT` | Entorno (development/production) | ❌ |
| `DEBUG` | Modo debug | ❌ |

## 🚢 Deployment

### Railway/Render

1. Crear cuenta y proyecto
2. Conectar repositorio GitHub
3. Configurar variables de entorno
4. Deploy automático en cada push

### Docker

```bash
# Construir imagen
docker build -t freelancer-backend .

# Ejecutar contenedor
docker run -p 8000:8000 --env-file .env freelancer-backend
```

## 📄 Licencia

MIT

## 👥 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 🆘 Soporte

Para problemas y preguntas, abrir un issue en GitHub.

---

Desarrollado con ❤️ para freelancers por freelancers