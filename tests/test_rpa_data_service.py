import json
import pytest

from app.schemas.rpa import (
    RpaDataCleanRequest,
    RpaDataCondition,
    RpaDataExtractRegexRequest,
    RpaDataFileReadRequest,
    RpaDataFileWriteRequest,
    RpaDataFilterRequest,
    RpaDataGroupCountRequest,
    RpaDataSortField,
    RpaDataSortRequest,
    RpaDataUniqueRequest,
)
from app.services.rpa.rpa_data_service import rpa_data_service


class TestCleanRows:
    def test_basic_clean_removes_empty_rows(self):
        request = RpaDataCleanRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "", "age": None},
                {"name": "Bob", "age": 25},
            ],
            dropEmptyRows=True,
            stripWhitespace=True,
            fillNa="",
        )
        result = rpa_data_service.clean_rows(request)
        assert result.success is True
        assert result.rowCount == 2

    def test_strip_whitespace(self):
        request = RpaDataCleanRequest(
            rows=[{"name": "  Alice  ", "age": 30}],
            stripWhitespace=True,
        )
        result = rpa_data_service.clean_rows(request)
        assert result.rows[0]["name"] == "Alice"

    def test_fill_na(self):
        request = RpaDataCleanRequest(
            rows=[{"name": "Alice", "age": None}],
            fillNa="N/A",
        )
        result = rpa_data_service.clean_rows(request)
        assert result.rows[0]["age"] == "N/A"

    def test_drop_empty_rows(self):
        request = RpaDataCleanRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": None, "age": None},
            ],
            dropEmptyRows=True,
        )
        result = rpa_data_service.clean_rows(request)
        assert result.rowCount == 1

    def test_keep_empty_rows_when_disabled(self):
        request = RpaDataCleanRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": None, "age": None},
            ],
            dropEmptyRows=False,
        )
        result = rpa_data_service.clean_rows(request)
        assert result.rowCount == 2

    def test_empty_input(self):
        request = RpaDataCleanRequest(rows=[])
        result = rpa_data_service.clean_rows(request)
        assert result.rowCount == 0
        assert result.rows == []


class TestFilterRows:
    def test_filter_eq(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="name", operator="==", value="Alice")],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"

    def test_filter_contains(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="name", operator="contains", value="li")],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"

    def test_filter_not_contains(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="name", operator="not_contains", value="li")],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Bob"

    def test_filter_gt(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="age", operator=">", value=26)],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"

    def test_filter_lt(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="age", operator="<", value=26)],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Bob"

    def test_filter_regex(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            conditions=[RpaDataCondition(column="name", operator="regex", value="^A")],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"

    def test_filter_in(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 35},
            ],
            conditions=[RpaDataCondition(column="name", operator="in", value=["Alice", "Bob"])],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 2

    def test_filter_not_in(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 35},
            ],
            conditions=[RpaDataCondition(column="name", operator="not_in", value=["Alice"])],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 2

    def test_filter_logic_and(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30},
            ],
            conditions=[
                RpaDataCondition(column="name", operator="==", value="Alice"),
                RpaDataCondition(column="age", operator="==", value=30),
            ],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[0]["age"] == 30

    def test_filter_logic_or(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 35},
            ],
            conditions=[
                RpaDataCondition(column="name", operator="==", value="Alice"),
                RpaDataCondition(column="age", operator="==", value=25),
            ],
            logic="or",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 2

    def test_filter_gte_lte(self):
        request = RpaDataFilterRequest(
            rows=[
                {"name": "A", "age": 30},
                {"name": "B", "age": 25},
                {"name": "C", "age": 20},
            ],
            conditions=[RpaDataCondition(column="age", operator=">=", value=25)],
            logic="and",
        )
        result = rpa_data_service.filter_rows(request)
        assert result.rowCount == 2


class TestSortRows:
    def test_sort_ascending(self):
        request = RpaDataSortRequest(
            rows=[
                {"name": "Charlie", "age": 35},
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            sortBy=[RpaDataSortField(column="name", ascending=True)],
        )
        result = rpa_data_service.sort_rows(request)
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[1]["name"] == "Bob"
        assert result.rows[2]["name"] == "Charlie"

    def test_sort_descending(self):
        request = RpaDataSortRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 35},
            ],
            sortBy=[RpaDataSortField(column="name", ascending=False)],
        )
        result = rpa_data_service.sort_rows(request)
        assert result.rows[0]["name"] == "Charlie"
        assert result.rows[2]["name"] == "Alice"

    def test_sort_multiple_fields(self):
        request = RpaDataSortRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 25},
            ],
            sortBy=[
                RpaDataSortField(column="name", ascending=True),
                RpaDataSortField(column="age", ascending=True),
            ],
        )
        result = rpa_data_service.sort_rows(request)
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[0]["age"] == 25
        assert result.rows[1]["name"] == "Alice"
        assert result.rows[1]["age"] == 30

    def test_sort_empty_fields_returns_original(self):
        request = RpaDataSortRequest(
            rows=[{"name": "Charlie"}, {"name": "Alice"}],
            sortBy=[],
        )
        result = rpa_data_service.sort_rows(request)
        assert result.rows[0]["name"] == "Charlie"
        assert result.rows[1]["name"] == "Alice"

    def test_sort_with_none_values(self):
        request = RpaDataSortRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": None},
                {"name": "Charlie", "age": 25},
            ],
            sortBy=[RpaDataSortField(column="age", ascending=True)],
        )
        result = rpa_data_service.sort_rows(request)
        assert result.rows[-1]["name"] == "Bob"


class TestUniqueRows:
    def test_unique_by_fields(self):
        request = RpaDataUniqueRequest(
            rows=[
                {"name": "Alice", "city": "NYC"},
                {"name": "Alice", "city": "LA"},
                {"name": "Bob", "city": "NYC"},
            ],
            subset=["name"],
            keep="first",
        )
        result = rpa_data_service.unique_rows(request)
        assert result.rowCount == 2
        assert result.rows[0]["city"] == "NYC"

    def test_unique_by_entire_row(self):
        request = RpaDataUniqueRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
        )
        result = rpa_data_service.unique_rows(request)
        assert result.rowCount == 2

    def test_no_duplicates(self):
        request = RpaDataUniqueRequest(
            rows=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
        )
        result = rpa_data_service.unique_rows(request)
        assert result.rowCount == 2


class TestGroupCount:
    def test_group_by_single_field(self):
        request = RpaDataGroupCountRequest(
            rows=[
                {"status": "active"},
                {"status": "active"},
                {"status": "inactive"},
            ],
            groupBy=["status"],
        )
        result = rpa_data_service.group_count(request)
        assert result.success is True
        assert result.rowCount == 2

    def test_group_by_multiple_fields(self):
        request = RpaDataGroupCountRequest(
            rows=[
                {"status": "active", "type": "A"},
                {"status": "active", "type": "A"},
                {"status": "active", "type": "B"},
            ],
            groupBy=["status", "type"],
        )
        result = rpa_data_service.group_count(request)
        assert result.rowCount == 2

    def test_empty_fields_raises(self):
        request = RpaDataGroupCountRequest(
            rows=[{"status": "active"}],
            groupBy=[],
        )
        with pytest.raises(ValueError, match="group_count"):
            rpa_data_service.group_count(request)


class TestExtractRegex:
    def test_named_groups(self):
        request = RpaDataExtractRegexRequest(
            text="alice@example.com bob@test.org",
            column="email",
            pattern=r"(?P<name>\w+)@(?P<domain>\w+\.\w+)",
        )
        result = rpa_data_service.extract_regex(request)
        assert result.success is True
        assert len(result.value) == 2

    def test_case_insensitive(self):
        request = RpaDataExtractRegexRequest(
            text="Hello HELLO hello",
            column="text",
            pattern=r"hello",
            caseSensitive=False,
        )
        result = rpa_data_service.extract_regex(request)
        assert result.success is True
        assert len(result.value) == 3

    def test_first_only(self):
        request = RpaDataExtractRegexRequest(
            text="alice@example.com bob@test.org",
            column="email",
            pattern=r"(?P<name>\w+)@(?P<domain>\w+\.\w+)",
            firstOnly=True,
        )
        result = rpa_data_service.extract_regex(request)
        assert result.success is True
        assert len(result.value) == 1


class TestReadFile:
    def test_file_not_found(self):
        request = RpaDataFileReadRequest(path="/nonexistent/file.csv")
        with pytest.raises(FileNotFoundError):
            rpa_data_service.read_file(request)

    def test_unsupported_format(self, tmp_path):
        file_path = tmp_path / "data.xyz"
        file_path.write_text("data", encoding="utf-8")
        request = RpaDataFileReadRequest(path=str(file_path))
        with pytest.raises(ValueError, match="暂不支持读取格式"):
            rpa_data_service.read_file(request)

    def test_read_csv(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
        request = RpaDataFileReadRequest(path=str(csv_path))
        result = rpa_data_service.read_file(request)
        assert result.success is True
        assert result.rowCount == 2
        assert result.rows[0]["name"] == "Alice"

    def test_read_json_list(self, tmp_path):
        json_path = tmp_path / "data.json"
        json_path.write_text(
            json.dumps([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]),
            encoding="utf-8",
        )
        request = RpaDataFileReadRequest(path=str(json_path))
        result = rpa_data_service.read_file(request)
        assert result.success is True
        assert result.rowCount == 2

    def test_read_json_dict_with_data_key(self, tmp_path):
        json_path = tmp_path / "data.json"
        json_path.write_text(
            json.dumps({"data": [{"name": "Alice"}]}),
            encoding="utf-8",
        )
        request = RpaDataFileReadRequest(path=str(json_path))
        result = rpa_data_service.read_file(request)
        assert result.rowCount == 1
        assert result.rows[0]["name"] == "Alice"


class TestWriteFile:
    def test_write_csv(self, tmp_path):
        csv_path = tmp_path / "output.csv"
        request = RpaDataFileWriteRequest(
            path=str(csv_path),
            rows=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        )
        result = rpa_data_service.write_file(request)
        assert result.success is True
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert "Alice" in content
        assert "Bob" in content

    def test_write_json(self, tmp_path):
        json_path = tmp_path / "output.json"
        request = RpaDataFileWriteRequest(
            path=str(json_path),
            rows=[{"name": "Alice", "age": 30}],
        )
        result = rpa_data_service.write_file(request)
        assert result.success is True
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["name"] == "Alice"

    def test_write_unsupported_format(self, tmp_path):
        file_path = tmp_path / "output.xyz"
        request = RpaDataFileWriteRequest(
            path=str(file_path),
            rows=[{"name": "Alice"}],
        )
        with pytest.raises(ValueError, match="暂不支持写出格式"):
            rpa_data_service.write_file(request)

    def test_write_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "output.csv"
        request = RpaDataFileWriteRequest(
            path=str(deep_path),
            rows=[{"name": "Alice"}],
        )
        result = rpa_data_service.write_file(request)
        assert result.success is True
        assert deep_path.exists()
