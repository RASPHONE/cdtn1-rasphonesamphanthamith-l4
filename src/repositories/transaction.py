from src.db import get_connection


def postgres_transaction():
    """
    Unit of work for PostgreSQL: one connection, one transaction.

    Services receive this factory through their constructor and use it as
    `with self.transaction() as tx:` to group several repository writes
    atomically (NFR5). Services never import the database module themselves,
    so unit tests can pass a fake transaction and run without PostgreSQL.
    """
    return get_connection()
