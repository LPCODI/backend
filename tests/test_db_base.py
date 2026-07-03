import unittest
from datetime import UTC, datetime

from sqlalchemy import String, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import (
    NAMING_CONVENTION,
    Base,
    BaseModel,
    BigIntPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
)


class SampleEntity(BaseModel):
    __tablename__ = "sample_entities"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


class DatabaseBaseTest(unittest.TestCase):
    def test_base_exports_single_metadata_with_naming_convention(self) -> None:
        self.assertIs(SampleEntity.metadata, Base.metadata)
        self.assertEqual(Base.metadata.naming_convention, NAMING_CONVENTION)
        self.assertEqual(Base.metadata.naming_convention["pk"], "pk_%(table_name)s")
        self.assertEqual(
            Base.metadata.naming_convention["fk"],
            "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        )

    def test_base_model_contains_common_columns(self) -> None:
        columns = SampleEntity.__table__.columns

        self.assertIn("id", columns)
        self.assertIn("created_at", columns)
        self.assertIn("updated_at", columns)
        self.assertIn("deleted_at", columns)
        self.assertTrue(columns["id"].primary_key)
        self.assertFalse(columns["created_at"].nullable)
        self.assertFalse(columns["updated_at"].nullable)
        self.assertTrue(columns["deleted_at"].nullable)
        self.assertTrue(columns["deleted_at"].index)

    def test_common_mixins_are_available_for_specialized_models(self) -> None:
        self.assertTrue(issubclass(BaseModel, BigIntPrimaryKeyMixin))
        self.assertTrue(issubclass(BaseModel, TimestampMixin))
        self.assertTrue(issubclass(BaseModel, SoftDeleteMixin))

    def test_postgresql_ddl_uses_bigint_identity_and_timestamptz(self) -> None:
        ddl = str(
            CreateTable(SampleEntity.__table__).compile(dialect=postgresql.dialect())
        ).upper()

        self.assertIn("ID BIGINT GENERATED ALWAYS AS IDENTITY", ddl)
        self.assertIn("CREATED_AT TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL", ddl)
        self.assertIn("UPDATED_AT TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL", ddl)
        self.assertIn("DELETED_AT TIMESTAMP WITH TIME ZONE", ddl)

    def test_metadata_can_create_common_columns_in_sqlite_test_database(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[SampleEntity.__table__])

        table_columns = {column["name"] for column in inspect(engine).get_columns("sample_entities")}
        self.assertGreaterEqual(
            table_columns,
            {"id", "name", "created_at", "updated_at", "deleted_at"},
        )

    def test_soft_delete_sets_timezone_aware_deleted_at(self) -> None:
        entity = SampleEntity(id=1, name="demo")

        self.assertFalse(entity.is_deleted)
        entity.soft_delete()

        self.assertTrue(entity.is_deleted)
        self.assertIsNotNone(entity.deleted_at)
        self.assertIs(entity.deleted_at.tzinfo, UTC)

    def test_soft_delete_accepts_explicit_timestamp(self) -> None:
        deleted_at = datetime(2026, 7, 3, 12, 0, tzinfo=UTC)
        entity = SampleEntity(id=1, name="demo")

        entity.soft_delete(deleted_at)

        self.assertIs(entity.deleted_at, deleted_at)

    def test_base_model_persists_with_common_columns_in_test_session(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[SampleEntity.__table__])

        with Session(engine) as session:
            entity = SampleEntity(id=1, name="demo")
            session.add(entity)
            session.commit()
            session.refresh(entity)

            self.assertEqual(entity.id, 1)
            self.assertEqual(entity.name, "demo")
            self.assertIsNotNone(entity.created_at)
            self.assertIsNotNone(entity.updated_at)
            self.assertIsNone(entity.deleted_at)


if __name__ == "__main__":
    unittest.main()
