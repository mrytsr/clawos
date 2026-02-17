from sqlmodel import SQLModel, create_engine

from config import WAREHOUSE_DB_URL
from models.warehouse_model import Warehouse, Product, Transaction


def main():
    if not WAREHOUSE_DB_URL:
        raise RuntimeError("Missing WAREHOUSE_DB_URL")
    engine = create_engine(WAREHOUSE_DB_URL, echo=False, pool_pre_ping=True)
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    main()
