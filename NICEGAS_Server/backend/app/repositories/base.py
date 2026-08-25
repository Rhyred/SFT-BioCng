from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel

from app.db.database import Base
from app.schemas.common import PaginatedResponse, PaginationMeta

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()
        
    def get_paginated(
        self, db: Session, *, page: int = 1, limit: int = 20, filters: Optional[List[Any]] = None
    ) -> PaginatedResponse:
        query = db.query(self.model)
        if filters:
            for f in filters:
                query = query.filter(f)
                
        total_count = query.count()
        
        skip = (page - 1) * limit
        items = query.offset(skip).limit(limit).all()
        
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        meta = PaginationMeta(
            total_count=total_count,
            current_page=page,
            limit=limit,
            total_pages=total_pages
        )
        return {"data": items, "meta": meta.model_dump()}

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj
