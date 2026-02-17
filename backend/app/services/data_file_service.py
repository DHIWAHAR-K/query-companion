"""Parse uploaded data files (CSV/TSV) into schema and preview rows."""
import base64
import csv
import io
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()

DATA_EXTENSIONS = (".csv", ".tsv")
PREVIEW_ROWS = 10


def _infer_type(values: List[Any]) -> str:
    """Infer column type from a list of string values."""
    if not values:
        return "TEXT"
    non_empty = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "TEXT"
    sample = non_empty[:100]
    all_int = True
    all_float = True
    for v in sample:
        s = str(v).strip()
        if not s:
            continue
        try:
            int(s)
        except ValueError:
            all_int = False
        try:
            float(s)
        except ValueError:
            all_float = False
    if all_int:
        return "INTEGER"
    if all_float:
        return "REAL"
    return "TEXT"


def parse_csv_from_base64(
    b64_data: str,
    filename: str,
    preview_rows: int = PREVIEW_ROWS,
) -> Optional[Dict[str, Any]]:
    """
    Decode base64 data and parse as CSV or TSV.
    Returns dict with: columns (list of {name, type}), rows (list of lists),
    schema_used (list of one SchemaTableUsed), label (str).
    Returns None on parse error.
    """
    try:
        raw = base64.b64decode(b64_data)
    except Exception as e:
        logger.warning("Failed to decode base64 attachment", error=str(e))
        return None
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to decode attachment as UTF-8", error=str(e))
        return None

    lower = filename.lower()
    delimiter = "\t" if lower.endswith(".tsv") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return None
    header = [h.strip() or f"col_{i}" for i, h in enumerate(rows[0])]
    data_rows = rows[1:]
    preview = data_rows[:preview_rows]
    columns_with_types = []
    for i, name in enumerate(header):
        col_values = [row[i] if i < len(row) else "" for row in data_rows]
        col_type = _infer_type(col_values)
        columns_with_types.append({"name": name, "type": col_type})
    table_name = "data"
    if "." in filename:
        table_name = filename.rsplit(".", 1)[0].replace(" ", "_").replace("-", "_") or "data"
    schema_used = [
        {
            "table_name": table_name,
            "schema_name": "public",
            "columns": [{"name": c["name"], "type": c["type"]} for c in columns_with_types],
        }
    ]
    return {
        "columns": columns_with_types,
        "rows": preview,
        "schema_used": schema_used,
        "label": f"Data preview: {filename} (first {len(preview)} rows)",
    }


def is_data_file_attachment(attachment: Any) -> bool:
    """Return True if attachment looks like a data file (e.g. CSV/TSV)."""
    if not attachment or not getattr(attachment, "filename", None):
        return False
    fn = (attachment.filename or "").lower()
    return fn.endswith(".csv") or fn.endswith(".tsv")


def get_first_data_file_parsed(attachments: Optional[List[Any]]) -> Optional[Dict[str, Any]]:
    """
    If attachments contains a data file, parse the first one and return
    the result of parse_csv_from_base64. Otherwise return None.
    """
    if not attachments:
        return None
    for att in attachments:
        if not is_data_file_attachment(att):
            continue
        data = getattr(att, "data", None)
        filename = getattr(att, "filename", "data.csv")
        if not data:
            continue
        result = parse_csv_from_base64(data, filename)
        if result:
            return result
    return None
