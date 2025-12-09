from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from app.config import settings

engine = create_async_engine(
    settings.database_url,  # подключение к БД
    echo=False,             # не логировать каждый SQL-запрос в консоль
    future=True             # использовать "новый" стиль SQLAlchemy 2.0
)

AsyncSessionLocal = sessionmaker(
    bind=engine,            # сессии будут работать с движком выше
    class_=AsyncSession,    # используем асинхронную сессию
    autocommit=False,       # коммит только вручную
    autoflush=False,        # не посылать изменения в БД автоматически
    expire_on_commit=False, # объекты не "протухают" после commit(), можно дальше читать их поля
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()