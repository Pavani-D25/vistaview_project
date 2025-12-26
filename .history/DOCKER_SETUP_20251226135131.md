# VistaView Docker Setup

## Quick Start

Run the backend in Docker:

```bash
# Build and start the backend
docker-compose up --build backend

# Or run in detached mode
docker-compose up -d --build backend
```

## Access the Application

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: Run separately with `cd frontend && npm run dev`

## Stop the Backend

```bash
docker-compose down
```

## View Logs

```bash
docker-compose logs -f backend
```

## Clean Restart

```bash
# Stop and remove containers
docker-compose down

# Rebuild and start
docker-compose up --build backend
```

## Notes

- The backend uses SQLite database stored in `backend/data/vistaview.sqlite`
- Images are stored in `backend/data/images/` and `backend/data/collages/`
- MinIO is disabled by default (using local storage)
- Hot reload is enabled for development
