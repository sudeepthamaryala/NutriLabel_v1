from collections.abc import Sequence

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw: object) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect: object):
        def process(value: Sequence[float] | str | None) -> str | None:
            if value is None or isinstance(value, str):
                return value
            if len(value) != self.dimensions:
                raise ValueError(f"Expected vector with {self.dimensions} dimensions")
            return "[" + ",".join(str(float(item)) for item in value) + "]"

        return process

