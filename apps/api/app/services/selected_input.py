"""Small designer-selected CSVs use the existing owned solution input snapshot.

No filesystem/remote references are accepted here. This is bounded inline data,
not an adjustable setting or a model-visible document upload.
"""
import base64
import csv
import io
import json

from fastapi import HTTPException

KEY = '$ai_effect_input'
MAX_CSV_BYTES = 60_000
MAX_JSON_BYTES = 65_536


def compile_input(value):
    if value is None:
        return None
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(encoded) > MAX_JSON_BYTES:
            raise ValueError('Run input must be at most 64 KiB of JSON.')
        if KEY not in value:
            return {'protocol': 'inline', 'uri': base64.b64encode(encoded).decode('ascii'), 'format': 'json'}
        item = value[KEY]
        if (set(value) != {KEY} or not isinstance(item, dict)
                or set(item) != {'schema_version', 'kind', 'name', 'content'}
                or item['schema_version'] != '1.0' or item['kind'] != 'inline_csv'
                or not isinstance(item['name'], str) or not 1 <= len(item['name']) <= 128
                or any(c in item['name'] for c in '/\\\x00\r\n')
                or not isinstance(item['content'], str)):
            raise ValueError('Select a supported CSV file again.')
        raw = item['content'].encode('utf-8')
        if not raw or len(raw) > MAX_CSV_BYTES or '\x00' in item['content']:
            raise ValueError('Select a UTF-8 CSV with at most 60,000 bytes.')
        rows = list(csv.reader(io.StringIO(item['content']), strict=True))
        if (len(rows) < 2 or not rows[0] or any(not header.strip() for header in rows[0])
                or len(set(rows[0])) != len(rows[0]) or any(len(row) != len(rows[0]) for row in rows[1:])):
            raise ValueError('CSV needs unique column names and data rows with the same number of columns.')
        return {'protocol': 'inline', 'uri': base64.b64encode(raw).decode('ascii'), 'format': 'csv'}
    except (ValueError, TypeError, UnicodeError, csv.Error) as exc:
        raise HTTPException(422, str(exc)) from None


def validate_metadata(metadata):
    if isinstance(metadata, dict) and metadata.get('run_input') is not None:
        compile_input(metadata['run_input'])
