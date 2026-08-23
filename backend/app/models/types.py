from app.extensions import db


# MySQL uses BIGINT for long-lived production identifiers. SQLite requires an
# exact INTEGER primary-key type for automatic rowid generation.
BIGINT = db.BigInteger().with_variant(db.Integer(), "sqlite")
