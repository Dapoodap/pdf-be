from sqlalchemy.orm import Session
from app.models.schema import Service, FileHistory

def get_or_create_service(db: Session, service_name: str) -> Service:
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        service = Service(name=service_name, description=f"Service for {service_name}")
        db.add(service)
        db.commit()
        db.refresh(service)
    return service

def log_file_history(db: Session, user_id: int | None, service_name: str, file_path: str, file_name: str, file_type: str) -> FileHistory:
    service = get_or_create_service(db, service_name)
    history = FileHistory(
        user_id=user_id,
        service_id=service.id,
        file_path=file_path,
        file_name=file_name,
        file_type=file_type
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
