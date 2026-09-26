from app.database import Base
from sqlalchemy.orm import mapped_column

class LedgerModel(Base):
    __tablename__ = "ledger_table"
    id = mapped_column(primary_key=True)
