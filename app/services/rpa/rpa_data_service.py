import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.schemas.rpa import (
    RpaDataCleanRequest,
    RpaDataCondition,
    RpaDataExtractRegexRequest,
    RpaDataFileReadRequest,
    RpaDataFileWriteRequest,
    RpaDataFilterRequest,
    RpaDataGroupCountRequest,
    RpaDataSortRequest,
    RpaDataTableResponse,
    RpaDataUniqueRequest,
    RpaDataValueResponse,
)


class RpaDataService:
    """RPA 数据处理公共方法层。

    这里对应影刀中常见的“数据表格/文本处理/列表处理”能力。
    规则：
    - 能用 pandas/openpyxl 这类成熟第三方库处理 CSV、Excel、JSON 时优先使用；
    - 没装第三方库或只是简单行数据处理时，使用标准库兜底；
    - 输入输出统一使用 list[dict]，方便 flow.run 的 JSON 步骤继续传递。
    """

    def clean_rows(self, request: RpaDataCleanRequest) -> RpaDataTableResponse:
        rows = [dict(row) for row in request.rows]
        cleaned: list[dict[str, Any]] = []
        rename_map = getattr(request, 'renameMap', None) or {}
        select_fields = getattr(request, 'selectFields', None) or []

        for row in rows:
            new_row: dict[str, Any] = {}
            for key, value in row.items():
                target_key = rename_map.get(key, key)
                if select_fields and target_key not in select_fields and key not in select_fields:
                    continue
                new_value = value
                if request.stripWhitespace and isinstance(new_value, str):
                    new_value = new_value.strip()
                if new_value is None and request.fillNa is not None:
                    new_value = request.fillNa
                new_row[target_key] = new_value

            if request.dropEmptyRows and self._is_empty_row(new_row):
                continue
            cleaned.append(new_row)

        return self._table_response(cleaned)

    def filter_rows(self, request: RpaDataFilterRequest) -> RpaDataTableResponse:
        """按条件过滤表格行，支持 equals/contains/gt/regex/empty 等常用条件。"""
        logic = request.logic.lower()
        if logic not in {'and', 'or'}:
            raise ValueError('logic 仅支持 and 或 or')

        result: list[dict[str, Any]] = []
        for row in request.rows:
            checks = [self._match_condition(row, condition) for condition in request.conditions]
            passed = all(checks) if logic == 'and' else any(checks)
            if passed:
                result.append(dict(row))
        return self._table_response(result)

    def sort_rows(self, request: RpaDataSortRequest) -> RpaDataTableResponse:
        rows = [dict(row) for row in request.rows]
        sort_fields = request.sortBy or []
        if not sort_fields:
            return self._table_response(rows)

        for item in reversed(sort_fields):
            field = item.column
            reverse = not item.ascending
            rows.sort(key=lambda row, f=field: self._sort_key(row.get(f)), reverse=reverse)
        return self._table_response(rows)

    def unique_rows(self, request: RpaDataUniqueRequest) -> RpaDataTableResponse:
        fields = request.subset or []
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in request.rows:
            if fields:
                key_data = {field: row.get(field) for field in fields}
            else:
                key_data = dict(row)
            key = json.dumps(key_data, ensure_ascii=False, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            result.append(dict(row))
        return self._table_response(result)

    def group_count(self, request: RpaDataGroupCountRequest) -> RpaDataTableResponse:
        fields = request.groupBy or []
        if not fields:
            raise ValueError('group_count 需要至少一个 groupBy')
        count_field = getattr(request, 'countField', None) or 'count'
        counter: Counter[tuple[Any, ...]] = Counter()
        for row in request.rows:
            counter[tuple(row.get(field) for field in fields)] += 1

        result: list[dict[str, Any]] = []
        for values, count in counter.items():
            item = {field: value for field, value in zip(fields, values, strict=False)}
            item[count_field] = count
            result.append(item)
        return self._table_response(result)

    def extract_regex(self, request: RpaDataExtractRegexRequest) -> RpaDataValueResponse:
        flags = 0
        if not request.caseSensitive:
            flags |= re.IGNORECASE
        if getattr(request, 'multiline', False):
            flags |= re.MULTILINE
        pattern = re.compile(request.pattern, flags)
        text = getattr(request, 'text', None) or ''
        matches = []
        for match in pattern.finditer(text):
            if match.groupdict():
                matches.append(match.groupdict())
            elif match.groups():
                matches.append(list(match.groups()))
            else:
                matches.append(match.group(0))
            if getattr(request, 'firstOnly', False):
                break
        return RpaDataValueResponse(success=True, value=matches, message=f'提取到 {len(matches)} 条')

    def read_file(self, request: RpaDataFileReadRequest) -> RpaDataTableResponse:
        path = Path(request.path)
        if not path.exists():
            raise FileNotFoundError(f'文件不存在: {path}')
        suffix = (getattr(request, 'format', None) or path.suffix.lstrip('.')).lower()
        if suffix in {'xlsx', 'xls'}:
            rows = self._read_excel_with_pandas(path, request.sheetName)
        elif suffix == 'csv':
            rows = self._read_csv(path, request.encoding)
        elif suffix == 'json':
            rows = self._read_json(path, request.encoding)
        else:
            raise ValueError(f'暂不支持读取格式: {suffix}')
        return self._table_response(rows)

    def write_file(self, request: RpaDataFileWriteRequest) -> RpaDataValueResponse:
        path = Path(request.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = (getattr(request, 'format', None) or path.suffix.lstrip('.')).lower()
        rows = [dict(row) for row in request.rows]
        if suffix in {'xlsx', 'xls'}:
            self._write_excel_with_pandas(path, rows, request.sheetName)
        elif suffix == 'csv':
            self._write_csv(path, rows, request.encoding)
        elif suffix == 'json':
            path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding=request.encoding)
        else:
            raise ValueError(f'暂不支持写出格式: {suffix}')
        return RpaDataValueResponse(success=True, value=str(path), message='文件写出完成')

    @staticmethod
    def _require_pandas():
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError('需要 pandas/openpyxl 支持，请先执行 uv sync') from exc
        return pd

    def _read_excel_with_pandas(self, path: Path, sheet_name: str | int | None) -> list[dict[str, Any]]:
        pd = self._require_pandas()
        df = pd.read_excel(path, sheet_name=0 if sheet_name is None else sheet_name)
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient='records')

    def _write_excel_with_pandas(self, path: Path, rows: list[dict[str, Any]], sheet_name: str | None) -> None:
        pd = self._require_pandas()
        df = pd.DataFrame(rows)
        df.to_excel(path, index=False, sheet_name=sheet_name or 'Sheet1')

    @staticmethod
    def _read_csv(path: Path, encoding: str) -> list[dict[str, Any]]:
        with path.open('r', encoding=encoding, newline='') as file:
            return [dict(row) for row in csv.DictReader(file)]

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]], encoding: str) -> None:
        fieldnames: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        with path.open('w', encoding=encoding, newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _read_json(path: Path, encoding: str) -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding=encoding))
        if isinstance(data, list):
            return [dict(item) if isinstance(item, dict) else {'value': item} for item in data]
        if isinstance(data, dict):
            # 常见接口返回可能是 {data:[...]}，优先取 data/list/rows/items。
            for key in ('data', 'list', 'rows', 'items'):
                value = data.get(key)
                if isinstance(value, list):
                    return [dict(item) if isinstance(item, dict) else {'value': item} for item in value]
            return [data]
        return [{'value': data}]

    @staticmethod
    def _is_empty_row(row: dict[str, Any]) -> bool:
        return all(value is None or (isinstance(value, str) and value.strip() == '') for value in row.values())

    @staticmethod
    def _sort_key(value: Any) -> tuple[int, Any]:
        if value is None:
            return (1, '')
        if isinstance(value, str):
            text = value.strip()
            try:
                return (0, float(text))
            except ValueError:
                return (0, text)
        return (0, value)

    def _match_condition(self, row: dict[str, Any], condition: RpaDataCondition) -> bool:
        actual = row.get(condition.column)
        expected = condition.value
        op = condition.operator.lower()
        if op in {'eq', 'equals', '=', '=='}:
            return actual == expected
        if op in {'ne', 'not_equals', '!='}:
            return actual != expected
        if op == 'contains':
            return str(expected) in str(actual or '')
        if op == 'not_contains':
            return str(expected) not in str(actual or '')
        if op == 'empty':
            return actual is None or str(actual).strip() == ''
        if op == 'not_empty':
            return actual is not None and str(actual).strip() != ''
        if op == 'regex':
            return re.search(str(expected or ''), str(actual or '')) is not None
        if op == 'in':
            return actual in (expected or []) if isinstance(expected, list) else actual == expected
        if op == 'not_in':
            return actual not in (expected or []) if isinstance(expected, list) else actual != expected
        if op in {'gt', '>', 'gte', '>=', 'lt', '<', 'lte', '<='}:
            left = self._to_number(actual)
            right = self._to_number(expected)
            if op in {'gt', '>'}:
                return left > right
            if op in {'gte', '>='}:
                return left >= right
            if op in {'lt', '<'}:
                return left < right
            return left <= right
        raise ValueError(f'不支持的数据过滤操作符: {condition.operator}')

    @staticmethod
    def _to_number(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'无法转换为数字: {value}') from exc

    @staticmethod
    def _table_response(rows: list[dict[str, Any]]) -> RpaDataTableResponse:
        columns: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)
        return RpaDataTableResponse(success=True, rowCount=len(rows), columns=columns, rows=rows)


rpa_data_service = RpaDataService()
