import csv
import pathlib

import pytest

import pixeltable as pxt

from ..utils import create_all_datatypes_tbl, create_test_tbl, validate_update_status


class TestCsv:
    def test_export_exact_output(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Verify exact CSV content for known data."""
        t = pxt.create_table('test_csv_exact', {'name': pxt.String, 'val': pxt.Int})
        t.insert([{'name': 'Alice', 'val': 1}, {'name': 'Bob', 'val': 2}])
        csv_path = tmp_path / 'exact.csv'
        pxt.io.export_csv(t, csv_path)
        with open(csv_path, encoding='utf-8') as f:
            rows = list(csv.reader(f))
        assert rows == [['name', 'val'], ['Alice', '1'], ['Bob', '2']]

    def test_export_round_trip(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Export a table to CSV, re-import, and verify equality."""
        t = create_test_tbl('test_csv_rt')
        csv_path = tmp_path / 'round_trip.csv'
        query = t.select(t.c1, t.c1n, t.c2, t.c3, t.c4)
        pxt.io.export_csv(query, csv_path)
        t2 = pxt.io.import_csv('test_csv_rt_reimported', str(csv_path))
        assert query.collect() == t2.collect()

    def test_export_with_nulls(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Nulls become empty strings in CSV."""
        t = pxt.create_table(
            'test_csv_nulls', {'c_int': pxt.Int, 'c_string': pxt.String, 'c_float': pxt.Float, 'c_json': pxt.Json}
        )
        t.insert(
            [
                {'c_int': 1, 'c_string': None, 'c_float': None, 'c_json': None},
                {'c_int': None, 'c_string': 'hello', 'c_float': 1.5, 'c_json': {'a': 1}},
            ]
        )
        csv_path = tmp_path / 'nulls.csv'
        pxt.io.export_csv(t, csv_path)
        with open(csv_path, encoding='utf-8') as f:
            exported = list(csv.DictReader(f))
        assert exported[0]['c_string'] == ''
        assert exported[0]['c_float'] == ''
        assert exported[0]['c_json'] == ''
        assert exported[1]['c_int'] == ''

    def test_export_with_query(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Test export with filtering and column selection."""
        t = pxt.create_table('test_csv_query', {'c_int': pxt.Int, 'c_string': pxt.String})
        validate_update_status(t.insert([{'c_int': i, 'c_string': f'row_{i}'} for i in range(10)]), expected_rows=10)

        csv_path = tmp_path / 'filtered.csv'
        pxt.io.export_csv(t.where(t.c_int < 5), csv_path)
        with open(csv_path, encoding='utf-8') as f:
            assert len(list(csv.DictReader(f))) == 5

        csv_path2 = tmp_path / 'subset.csv'
        pxt.io.export_csv(t.select(t.c_string), csv_path2)
        with open(csv_path2, encoding='utf-8') as f:
            exported = list(csv.DictReader(f))
        assert len(exported) == 10
        assert list(exported[0].keys()) == ['c_string']

    @pytest.mark.parametrize('delimiter', [',', '\t', '|'])
    def test_export_delimiter(self, uses_db: None, tmp_path: pathlib.Path, delimiter: str) -> None:
        """Test CSV export with various delimiters."""
        t = pxt.create_table('test_csv_delim', {'c_int': pxt.Int, 'c_string': pxt.String})
        t.insert([{'c_int': 1, 'c_string': 'hello'}, {'c_int': 2, 'c_string': 'world'}])
        csv_path = tmp_path / 'delimited.csv'
        pxt.io.export_csv(t, csv_path, delimiter=delimiter)
        with open(csv_path, encoding='utf-8') as f:
            exported = list(csv.DictReader(f, delimiter=delimiter))
        assert len(exported) == 2
        assert int(exported[0]['c_int']) == 1
        assert exported[1]['c_string'] == 'world'

    def test_export_excludes_media_and_binary(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Media and binary columns are excluded from CSV export."""
        t = create_all_datatypes_tbl()
        csv_path = tmp_path / 'all_types.csv'
        pxt.io.export_csv(t, csv_path)
        with open(csv_path, encoding='utf-8') as f:
            headers = csv.DictReader(f).fieldnames or []
        for excluded in ['c_image', 'c_video', 'c_audio', 'c_document', 'c_binary']:
            assert excluded not in headers, f'{excluded} should be excluded'

    def test_export_nan_inf(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """NaN and Inf float values become empty strings."""
        t = pxt.create_table('test_csv_nan', {'c_float': pxt.Float})
        t.insert([{'c_float': float('nan')}, {'c_float': float('inf')}, {'c_float': float('-inf')}, {'c_float': 1.5}])
        csv_path = tmp_path / 'nan.csv'
        pxt.io.export_csv(t, csv_path)
        with open(csv_path, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        assert rows[0]['c_float'] == ''
        assert rows[1]['c_float'] == ''
        assert rows[2]['c_float'] == ''
        assert rows[3]['c_float'] == '1.5'

    def test_export_empty_table(self, uses_db: None, tmp_path: pathlib.Path) -> None:
        """Exporting a table with 0 rows produces header-only CSV."""
        t = pxt.create_table('test_csv_empty', {'c_int': pxt.Int, 'c_string': pxt.String})
        csv_path = tmp_path / 'empty.csv'
        pxt.io.export_csv(t, csv_path)
        with open(csv_path, encoding='utf-8') as f:
            rows = list(csv.reader(f))
        assert rows == [['c_int', 'c_string']]
