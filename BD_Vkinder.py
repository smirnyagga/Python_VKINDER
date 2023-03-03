import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()
class Options(Base):
    __tablename__ = "options"

    user_id = sq.Column(sq.Integer)
    option_id = sq.Column(sq.Integer, primary_key=True)
    foto = sq.Column(sq.String)
    white_list = sq.Column(sq.String)

def create_tables(engine):
    # Base.metadata.drop_all(engine) #надо будет убрать, чтобы не попадали контакты уже используемые
    Base.metadata.create_all(engine)

DSN = "postgresql://postgres:4815162342@localhost:5432/cleintsdb"
engine = sq.create_engine(DSN)


# сессия
Session = sessionmaker(bind=engine)
sessiondb = Session()

