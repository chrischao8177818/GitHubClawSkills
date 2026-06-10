#!/usr/bin/env python
"""Maintain and query a lightweight purchase price history ledger."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


DEFAULT_ROOT = Path("price-history")
DEFAULT_OLD_ARTIFACT_LEDGER = Path("artifacts/price-history/ledger.jsonl")
DEFAULT_CURRENCY = "NT$"
UNKNOWN = "待確認"


QUERY_STOPWORDS = (
    "歷史價格",
    "歷史金額",
    "歷史價錢",
    "歷史",
    "最高最低平均",
    "最高",
    "最低",
    "平均",
    "最近一次",
    "最近",
    "價格",
    "金額",
    "價錢",
    "買貴嗎",
    "貴嗎",
    "查詢",
    "查一下",
    "請問",
    "幫我查",
)


@dataclass
class PriceRecord:
    date: str
    merchant: str
    item_name: str
    canonical_item: str
    query_group: str
    category: str
    quantity: Any
    unit_price: Any
    subtotal: Any
    currency: str
    source_comment_id: str
    status: str
    notes: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PriceRecord":
        return cls(
            date=str(raw.get("date", UNKNOWN)),
            merchant=str(raw.get("merchant", UNKNOWN)),
            item_name=str(raw.get("item_name", UNKNOWN)),
            canonical_item=str(raw.get("canonical_item", raw.get("item_name", UNKNOWN))),
            query_group=str(raw.get("query_group", raw.get("canonical_item", raw.get("item_name", UNKNOWN)))),
            category=str(raw.get("category", "其他")),
            quantity=raw.get("quantity", UNKNOWN),
            unit_price=raw.get("unit_price", UNKNOWN),
            subtotal=raw.get("subtotal", UNKNOWN),
            currency=str(raw.get("currency", DEFAULT_CURRENCY)),
            source_comment_id=str(raw.get("source_comment_id", UNKNOWN)),
            status=str(raw.get("status", "pending")),
            notes=str(raw.get("notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "merchant": self.merchant,
            "item_name": self.item_name,
            "canonical_item": self.canonical_item,
            "query_group": self.query_group,
            "category": self.category,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
            "currency": self.currency,
            "source_comment_id": self.source_comment_id,
            "status": self.status,
            "notes": self.notes,
        }


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    return text


def normalize_query(query: str) -> str:
    normalized = normalize_text(query)
    for word in QUERY_STOPWORDS:
        normalized = normalized.replace(normalize_text(word), "")
    return normalized or normalize_text(query)


def parse_money(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value or "").strip()
    if text in {"", UNKNOWN, "-", "null", "None"}:
        return None
    cleaned = re.sub(r"[^\d.-]", "", text)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return int(round(float(cleaned)))
    except ValueError:
        return None


def parse_quantity(value: Any) -> Any:
    if value in (None, "", UNKNOWN):
        return UNKNOWN
    try:
        number = float(str(value).strip())
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def parse_date(value: str | None) -> str:
    if not value:
        return date.today().isoformat()
    value = value.strip().replace("/", "-")
    if re.fullmatch(r"\d{1,2}-\d{1,2}", value):
        value = f"{date.today().year}-{value}"
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.date().isoformat()


def read_ledger(path: Path) -> list[PriceRecord]:
    if not path.exists():
        return []
    records: list[PriceRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(PriceRecord.from_dict(json.loads(line)))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSONL") from exc
    return records


def append_record(path: Path, record: PriceRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n")


def month_path(root: Path, record_date: str) -> Path:
    parsed = datetime.strptime(record_date, "%Y-%m-%d").date()
    return root / "entries" / f"{parsed.year:04d}" / f"{parsed.month:02d}.jsonl"


def index_path(root: Path) -> Path:
    return root / "indexes" / "item-summary.json"


def iter_entry_files(root: Path) -> list[Path]:
    entries = root / "entries"
    if not entries.exists():
        return []
    return sorted(entries.glob("*/*.jsonl"))


def read_root_records(root: Path) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    for path in iter_entry_files(root):
        records.extend(read_ledger(path))
    return records


def read_records(root: Path, ledger: Path | None = None) -> list[PriceRecord]:
    if ledger is not None:
        return read_ledger(ledger)
    return read_root_records(root)


def append_record_to_root(root: Path, record: PriceRecord) -> Path:
    path = month_path(root, record.date)
    append_record(path, record)
    return path


def duplicate_key(record: PriceRecord) -> tuple[str, str, str, str, str, str] | None:
    if not record.source_comment_id or record.source_comment_id == UNKNOWN:
        return None
    return (
        normalize_text(record.source_comment_id),
        record.date,
        normalize_text(record.merchant),
        normalize_text(record.item_name),
        normalize_text(record.quantity),
        normalize_text(record.unit_price),
    )


def append_unique_records(root: Path, records: list[PriceRecord], ledger: Path | None = None) -> tuple[int, int]:
    existing_records = read_records(root, ledger)
    existing_keys = {key for record in existing_records if (key := duplicate_key(record)) is not None}
    added = 0
    skipped = 0
    for record in records:
        key = duplicate_key(record)
        if key is not None and key in existing_keys:
            skipped += 1
            continue
        if ledger is not None:
            append_record(ledger, record)
        else:
            append_record_to_root(root, record)
        if key is not None:
            existing_keys.add(key)
        added += 1
    if added and ledger is None:
        rebuild_index(root)
    return added, skipped


def build_record(args: argparse.Namespace) -> PriceRecord:
    unit_price = parse_money(args.unit_price)
    quantity = parse_quantity(args.quantity)
    subtotal = parse_money(args.subtotal)
    if subtotal is None and unit_price is not None and isinstance(quantity, (int, float)):
        subtotal = int(round(unit_price * quantity))

    status = args.status
    if status == "auto":
        status = "confirmed" if unit_price is not None else "pending"

    item_name = args.item_name or UNKNOWN
    canonical_item = args.canonical_item or item_name
    query_group = args.query_group or canonical_item

    return PriceRecord(
        date=parse_date(args.date),
        merchant=args.merchant or UNKNOWN,
        item_name=item_name,
        canonical_item=canonical_item,
        query_group=query_group,
        category=args.category or "其他",
        quantity=quantity,
        unit_price=unit_price if unit_price is not None else UNKNOWN,
        subtotal=subtotal if subtotal is not None else UNKNOWN,
        currency=args.currency or DEFAULT_CURRENCY,
        source_comment_id=args.source_comment_id or UNKNOWN,
        status=status,
        notes=args.notes or "",
    )


def build_record_from_dict(raw: dict[str, Any]) -> PriceRecord:
    defaults = {
        "date": None,
        "merchant": UNKNOWN,
        "item_name": None,
        "canonical_item": None,
        "query_group": None,
        "category": "其他",
        "quantity": 1,
        "unit_price": UNKNOWN,
        "subtotal": None,
        "currency": DEFAULT_CURRENCY,
        "source_comment_id": UNKNOWN,
        "status": "auto",
        "notes": "",
    }
    values = {**defaults, **raw}
    if not values["item_name"]:
        raise ValueError("each batch item requires item_name")
    return build_record(argparse.Namespace(**values))


def confirmed(records: Iterable[PriceRecord]) -> list[PriceRecord]:
    return [record for record in records if record.status == "confirmed" and parse_money(record.unit_price) is not None]


def sort_by_date(records: Iterable[PriceRecord]) -> list[PriceRecord]:
    return sorted(records, key=lambda record: record.date)


def money(value: int | None, currency: str = DEFAULT_CURRENCY) -> str:
    return UNKNOWN if value is None else f"{currency}{value:,}"


def average_price(records: Iterable[PriceRecord]) -> int | None:
    prices = [parse_money(record.unit_price) for record in records]
    prices = [price for price in prices if price is not None]
    if not prices:
        return None
    return int(round(mean(prices)))


def record_price(record: PriceRecord) -> int | None:
    return parse_money(record.unit_price)


def latest_record(records: list[PriceRecord]) -> PriceRecord | None:
    usable = sort_by_date(confirmed(records))
    return usable[-1] if usable else None


def stats_payload(records: list[PriceRecord]) -> dict[str, Any]:
    usable = sort_by_date(confirmed(records))
    prices = [record_price(record) for record in usable]
    numeric_prices = [price for price in prices if price is not None]
    latest = latest_record(records)
    return {
        "confirmed_count": len(usable),
        "pending_count": len(records) - len(usable),
        "latest_date": latest.date if latest else None,
        "latest_price": record_price(latest) if latest else None,
        "highest_price": max(numeric_prices) if numeric_prices else None,
        "lowest_price": min(numeric_prices) if numeric_prices else None,
        "average_price": average_price(usable),
    }


def write_summary_index(root: Path, records: list[PriceRecord]) -> Path:
    by_item: dict[str, list[PriceRecord]] = {}
    by_group: dict[str, list[PriceRecord]] = {}
    for record in records:
        if record.canonical_item and record.canonical_item != UNKNOWN:
            by_item.setdefault(record.canonical_item, []).append(record)
        if record.query_group and record.query_group != UNKNOWN:
            by_group.setdefault(record.query_group, []).append(record)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "record_count": len(records),
        "items": {name: stats_payload(item_records) for name, item_records in sorted(by_item.items())},
        "groups": {name: stats_payload(group_records) for name, group_records in sorted(by_group.items())},
    }
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def rebuild_index(root: Path) -> Path:
    return write_summary_index(root, read_root_records(root))


def exact_matches(records: list[PriceRecord], query: str) -> list[PriceRecord]:
    normalized = normalize_query(query)
    return [
        record
        for record in records
        if normalized in {normalize_text(record.item_name), normalize_text(record.canonical_item)}
    ]


def group_matches(records: list[PriceRecord], query: str) -> list[PriceRecord]:
    normalized = normalize_query(query)
    return [record for record in records if normalized == normalize_text(record.query_group)]


def similar_candidates(records: list[PriceRecord], query: str) -> list[str]:
    normalized = normalize_query(query)
    values = sorted(
        {
            value
            for record in records
            for value in (record.item_name, record.canonical_item, record.query_group)
            if value and value != UNKNOWN
        }
    )
    substring_matches = [value for value in values if normalized in normalize_text(value) or normalize_text(value) in normalized]
    if substring_matches:
        return substring_matches[:8]
    normalized_map = {normalize_text(value): value for value in values}
    close = difflib.get_close_matches(normalized, list(normalized_map), n=8, cutoff=0.35)
    return [normalized_map[item] for item in close]


def render_stats(title: str, records: list[PriceRecord], all_matched: list[PriceRecord]) -> str:
    usable = sort_by_date(confirmed(records))
    pending_count = len(all_matched) - len(confirmed(all_matched))
    if not usable:
        return f"# {title}\n\n目前沒有可計算的 confirmed 價格紀錄。\n\n待確認紀錄：{pending_count} 筆\n"

    prices = [record_price(record) for record in usable]
    numeric_prices = [price for price in prices if price is not None]
    latest = usable[-1]
    latest_price = record_price(latest)
    currency = latest.currency or DEFAULT_CURRENCY

    lines = [
        f"# {title}",
        "",
        "| 指標 | 金額 |",
        "|------|------|",
        f"| 最近一次 | {money(latest_price, currency)} |",
        f"| 最高價 | {money(max(numeric_prices), currency)} |",
        f"| 最低價 | {money(min(numeric_prices), currency)} |",
        f"| 平均價 | {money(average_price(usable), currency)} |",
        f"| 可計算次數 | {len(usable)} |",
    ]
    if pending_count:
        lines.append(f"| 待確認紀錄 | {pending_count} 筆 |")

    lines.extend(
        [
            "",
            "## 歷史明細",
            "",
            "| 日期 | 商家 | 品項 | 單價 | 備註 |",
            "|------|------|------|------|------|",
        ]
    )
    for record in usable:
        lines.append(
            f"| {record.date} | {record.merchant} | {record.canonical_item} | "
            f"{money(record_price(record), record.currency)} | {record.notes or '-'} |"
        )
    return "\n".join(lines) + "\n"


def render_candidates(query: str, records: list[PriceRecord]) -> str:
    grouped: dict[str, list[PriceRecord]] = {}
    for record in records:
        grouped.setdefault(record.canonical_item, []).append(record)

    lines = [
        f"# {query}相關品項",
        "",
        f"找到 {len(grouped)} 種可能的品項：",
        "",
        "| 品項 | 次數 | 最近價格 | 平均價格 | 最低 | 最高 |",
        "|------|------|----------|----------|------|------|",
    ]
    for item, item_records in sorted(grouped.items()):
        usable = sort_by_date(confirmed(item_records))
        if not usable:
            lines.append(f"| {item} | 0 | {UNKNOWN} | {UNKNOWN} | {UNKNOWN} | {UNKNOWN} |")
            continue
        prices = [record_price(record) for record in usable]
        numeric_prices = [price for price in prices if price is not None]
        latest = usable[-1]
        currency = latest.currency or DEFAULT_CURRENCY
        lines.append(
            f"| {item} | {len(usable)} | {money(record_price(latest), currency)} | "
            f"{money(average_price(usable), currency)} | {money(min(numeric_prices), currency)} | "
            f"{money(max(numeric_prices), currency)} |"
        )
    lines.extend(["", "請指定要查哪一種品項，或回覆 `全部` 查看整個種類彙總。"])
    return "\n".join(lines) + "\n"


def render_no_match(query: str, records: list[PriceRecord]) -> str:
    candidates = similar_candidates(records, query)
    lines = [f"# {query}", "", "目前沒有找到可用的歷史價格紀錄。"]
    if candidates:
        lines.extend(["", "可能相關的既有品項：", ""])
        lines.extend([f"- {candidate}" for candidate in candidates])
    return "\n".join(lines) + "\n"


def query_price(root: Path, query: str, include_all_group: bool = False, ledger: Path | None = None) -> str:
    records = read_records(root, ledger)
    if not records:
        return "# 價格歷史\n\n目前還沒有任何價格歷史資料。\n"

    exact = exact_matches(records, query)
    if exact:
        title = exact[0].canonical_item if len({record.canonical_item for record in exact}) == 1 else query
        return render_stats(f"{title}歷史價格", exact, exact)

    grouped = group_matches(records, query)
    if grouped:
        items = {record.canonical_item for record in grouped}
        if len(items) > 1 and not include_all_group:
            return render_candidates(normalize_query(query), grouped)
        return render_stats(f"{normalize_query(query)}歷史價格", grouped, grouped)

    return render_no_match(query, records)


def handle_add_entry(args: argparse.Namespace) -> int:
    record = build_record(args)
    root = Path(args.root)
    ledger = Path(args.ledger) if args.ledger else None
    added, skipped = append_unique_records(root, [record], ledger)
    print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
    print(f"added {added}, skipped {skipped} duplicate")
    return 0


def handle_add_batch(args: argparse.Namespace) -> int:
    source = Path(args.input)
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict):
        items = raw.get("items") if "items" in raw else [raw]
    else:
        items = raw
    if not isinstance(items, list):
        raise ValueError("batch input must be a JSON item, an array, or an object with an items array")
    records = [build_record_from_dict(item) for item in items]
    root = Path(args.root)
    ledger = Path(args.ledger) if args.ledger else None
    added, skipped = append_unique_records(root, records, ledger)
    print(f"added {added}, skipped {skipped} duplicate")
    return 0


def handle_query_price(args: argparse.Namespace) -> int:
    ledger = Path(args.ledger) if args.ledger else None
    print(query_price(Path(args.root), args.query, args.all, ledger), end="")
    return 0


def handle_rebuild_index(args: argparse.Namespace) -> int:
    path = rebuild_index(Path(args.root))
    print(f"rebuilt {path}")
    return 0


def handle_migrate_ledger(args: argparse.Namespace) -> int:
    source = Path(args.source)
    root = Path(args.root)
    records = read_ledger(source)
    if not records:
        print(f"no records found in {source}")
        return 0
    existing = {
        json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in read_root_records(root)
    }
    migrated = 0
    skipped = 0
    for record in records:
        key = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key in existing:
            skipped += 1
            continue
        append_record_to_root(root, record)
        existing.add(key)
        migrated += 1
    index = rebuild_index(root)
    print(f"migrated {migrated} records from {source}")
    if skipped:
        print(f"skipped {skipped} duplicate records")
    print(f"rebuilt {index}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record and query purchase price history.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Root directory for price history data.")
    parser.add_argument("--ledger", help="Optional legacy single-file ledger.jsonl override.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add-entry", help="Append one purchase item unless it already exists.")
    add.add_argument("--date", help="Purchase date. Supports YYYY-MM-DD, YYYY/MM/DD, or MM-DD.")
    add.add_argument("--merchant", default=UNKNOWN)
    add.add_argument("--item-name", required=True)
    add.add_argument("--canonical-item")
    add.add_argument("--query-group")
    add.add_argument("--category", default="其他")
    add.add_argument("--quantity", default=1)
    add.add_argument("--unit-price", required=True)
    add.add_argument("--subtotal")
    add.add_argument("--currency", default=DEFAULT_CURRENCY)
    add.add_argument("--source-comment-id", default=UNKNOWN)
    add.add_argument("--status", choices=("auto", "confirmed", "pending"), default="auto")
    add.add_argument("--notes", default="")
    add.set_defaults(func=handle_add_entry)

    batch = subparsers.add_parser("add-batch", help="Append purchase items from a JSON file and skip duplicates.")
    batch.add_argument("--input", required=True, help="JSON array or object with an items array.")
    batch.set_defaults(func=handle_add_batch)

    query = subparsers.add_parser("query-price", help="Query item or group price history.")
    query.add_argument("query")
    query.add_argument("--all", action="store_true", help="Summarize a whole query group even when it contains multiple items.")
    query.set_defaults(func=handle_query_price)

    rebuild = subparsers.add_parser("rebuild-index", help="Rebuild indexes/item-summary.json from entries.")
    rebuild.set_defaults(func=handle_rebuild_index)

    migrate = subparsers.add_parser("migrate-ledger", help="Migrate a legacy ledger.jsonl into monthly entry files.")
    migrate.add_argument("--source", default=str(DEFAULT_OLD_ARTIFACT_LEDGER))
    migrate.set_defaults(func=handle_migrate_ledger)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
