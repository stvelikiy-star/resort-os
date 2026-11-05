"""Exercise the production grid with a trusted property unlike server default."""
import ast
import asyncio
from datetime import date
from pathlib import Path
from typing import Any
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "services/api/app/main.py"
function = next(node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.AsyncFunctionDef) and node.name == "pms_grid")
function.decorator_list = []
function.args.defaults[-1] = ast.Constant(None)
module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), function], type_ignores=[])
ast.fix_missing_locations(module)


class Connection:
    def __init__(self):
        self.boundaries = []

    async def fetch(self, query, property_id, *_):
        self.boundaries.append(property_id)
        return []


class Acquisition:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *_):
        return False


async def main():
    for code in ("HOTEL_A", "HOTEL_B"):
        connection = Connection()
        async def trusted_property_id(conn, user):
            assert conn is connection
            return user["property_id"]
        ns = {"PROPERTY_CODE": "LEGACY_SERVER_DEFAULT", "trusted_property_id": trusted_property_id, "date": date, "Any": Any}
        exec(compile(module, str(SOURCE), "exec"), ns)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=SimpleNamespace(acquire=lambda: Acquisition(connection)))))
        user = {"role": "OWNER", "property_code": code, "property_id": code + "_ID"}
        result = await ns["pms_grid"](request, date(2027, 8, 1), date(2027, 8, 2), _user=user)
        assert result["property"] == code, result
        assert connection.boundaries == [user["property_id"], user["property_id"]], connection.boundaries
        print(f"PASS: {code} grid data and label use authenticated property")


if __name__ == "__main__":
    asyncio.run(main())
