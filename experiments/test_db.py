
from sqlalchemy import text

from src.database import SessionFactory, engine

# Create an isolated table for this experiment.
with engine.begin() as connection:
    connection.execute(
        text("""
            CREATE TABLE IF NOT EXISTS transaction_test (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
    )

try:
    # Successful exit automatically commits.
    with SessionFactory.begin() as session:
        session.execute(
            text("""
                INSERT INTO transaction_test (id, name)
                VALUES (2, 'commit-demo')
            """)
        )

        print("Test record inserted inside transaction.")

    print("Transaction committed successfully.")

    # Verify using a separate session.
    with SessionFactory() as session:
        result = session.execute(
            text("""
                SELECT name
                FROM transaction_test
                WHERE id = 2
            """)
        )

        name = result.scalar_one()
        print("Persisted record:", name)

finally:
    # Clean up the experiment table.
    with engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS transaction_test")
        )

    print("Experiment table removed.")
