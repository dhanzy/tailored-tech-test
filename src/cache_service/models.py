from sqlmodel import Field, SQLModel


class TransformedString(SQLModel, table=True):
    """Cached result of one transformer call, keyed by its input string.

    Caching per string (not per payload) is what lets two payloads that merely
    share some strings avoid calling the transformer again for those strings.
    """

    source: str = Field(primary_key=True)
    result: str


class Payload(SQLModel, table=True):
    """A generated payload, keyed by a hash of the input that produced it."""

    id: str = Field(primary_key=True)
    output: str
