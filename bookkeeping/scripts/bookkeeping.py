#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

DETAIL_HEADERS = ["日期", "品項", "分類", "數量", "單價", "小計", "備註"]
DEFAULT_EXCLUDED_CATEGORIES = {"信用卡帳單"}
MONTH_RE = re.compile(r"^(?P<year>\d{4})[-/](?P<month>\d{1,2})$")
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]+'


@dataclass
class Row:
    source_file: Path
    date_text: str
    item: str
    category: str
    quantity: Decimal | None
    unit_price: Decimal | None
    subtotal: Decimal | None
    note: str


def normalize_month(value: str) -> tuple[int, int]:
    match = MONTH_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid month format: {value!r}. Use YYYY-MM or YYYY/MM.")
    year = int(match.group("year"))
    month = int(match.group("month"))
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month number: {month}")
    return year, month


def month_dir(root: Path, year: int, month: int) -> Path:
    return root / f"{year}" / f"{month:02d}"


def slugify(text: str) -> str:
    value = text.strip()
    value = re.sub(INVALID_FILENAME_CHARS, "-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    value = value.strip(" .-_")
    return value or "entry"


def parse_decimal(text: str) -> Decimal | None:
    value = text.strip()
    if not value or value in {"-", "待確認", "—", "N/A"}:
        return None
    value = value.replace("NT$", "").replace("$", "").replace(",", "")
    value = value.strip()
    if not value or value in {"-", "待確認", "—", "N/A"}:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_quantity(text: str) -> Decimal | None:
    return parse_decimal(text)


def format_money(value: Decimal) -> str:
    value = value.normalize()
    if value == value.to_integral():
        return f"NT${int(value):,}"
    text = format(value, "f").rstrip("0").rstrip(".")
    return f"NT${text}"


def format_percent(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.1')):.1f}%"


def decimal_plain(value: Decimal) -> str:
    if value == value.to_integral():
        return str(int(value))
    return format(value, "f").rstrip("0").rstrip(".")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def create_entry(args: argparse.Namespace) -> Path:
    if args.date:
        year, month, day = map(int, args.date.split("-"))
        entry_date = date(year, month, day)
    else:
        entry_date = date.today()
    root = Path(args.root)
    target_dir = month_dir(root, entry_date.year, entry_date.month)
    target_dir.mkdir(parents=True, exist_ok=True)

    title = args.title.strip() if args.title else "未命名記帳"
    stem = f"{entry_date:%Y-%m-%d}__{slugify(title)}"
    target = target_dir / f"{stem}.md"
    if target.exists() and not args.overwrite:
        suffix = 2
        while True:
            candidate = target_dir / f"{stem}-{suffix}.md"
            if not candidate.exists():
                target = candidate
                break
            suffix += 1

    source = f"source: {args.source}" if args.source else "source: manual"
    content = f"""---
date: {entry_date:%Y-%m-%d}
title: {title}
{source}
---

# 記帳整理結果

## 明細

| 日期 | 品項 | 分類 | 數量 | 單價 | 小計 | 備註 |
|------|------|------|------|------|------|------|

## 分類小計

| 分類 | 金額 |
|------|------|

## 總計

| 項目 | 金額 |
|------|------|
| 合計 | 待確認 |
"""
    write_text(target, content)
    return target


def is_table_separator(row: list[str]) -> bool:
    if not row:
        return False
    for cell in row:
        stripped = cell.strip()
        if not stripped:
            continue
        if not re.fullmatch(r":?-{3,}:?", stripped):
            return False
    return True


def parse_table_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def extract_detail_rows(path: Path) -> list[Row]:
    lines = load_text(path).splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+明細\s*$", line.strip()):
            start = idx + 1
            break
    if start is None:
        return []

    while start < len(lines) and not lines[start].strip().startswith("|"):
        if lines[start].strip().startswith("#"):
            return []
        start += 1
    if start >= len(lines) - 1:
        return []

    header = parse_table_row(lines[start])
    separator = parse_table_row(lines[start + 1])
    if len(header) < len(DETAIL_HEADERS) or not is_table_separator(separator):
        return []

    column_index = {name: header.index(name) for name in DETAIL_HEADERS if name in header}
    if len(column_index) < len(DETAIL_HEADERS):
        return []

    rows: list[Row] = []
    for line in lines[start + 2 :]:
        stripped = line.strip()
        if not stripped:
            break
        if not stripped.startswith("|"):
            break
        if is_table_separator(parse_table_row(line)):
            continue
        cells = parse_table_row(line)
        if len(cells) < len(header):
            cells.extend([""] * (len(header) - len(cells)))
        date_text = cells[column_index["日期"]].strip()
        item = cells[column_index["品項"]].strip() or "待確認"
        category = cells[column_index["分類"]].strip() or "待確認"
        quantity = parse_quantity(cells[column_index["數量"]])
        unit_price = parse_decimal(cells[column_index["單價"]])
        subtotal = parse_decimal(cells[column_index["小計"]])
        note = cells[column_index["備註"]].strip()
        if subtotal is None and quantity is not None and unit_price is not None:
            subtotal = quantity * unit_price
        rows.append(
            Row(
                source_file=path,
                date_text=date_text,
                item=item,
                category=category,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                note=note,
            )
        )
    return rows


def collect_rows(month_path: Path) -> list[Row]:
    rows: list[Row] = []
    for path in sorted(month_path.glob("*.md")):
        if path.name in {"summary.md", "summary.svg", "monthly-list.md"}:
            continue
        rows.extend(extract_detail_rows(path))
    return rows


def build_svg(month_label: str, category_totals: list[tuple[str, Decimal]], output_path: Path) -> None:
    width = 820
    height = 420
    cx = 180
    cy = 190
    radius = 120
    colors = [
        "#0f766e",
        "#2563eb",
        "#ea580c",
        "#7c3aed",
        "#059669",
        "#dc2626",
        "#ca8a04",
        "#0891b2",
        "#4f46e5",
        "#9333ea",
    ]

    total = sum((amount for _, amount in category_totals), Decimal("0"))
    legend_x = 360
    legend_y = 70
    legend_gap = 28

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="40" y="42" font-size="26" font-family="Arial, sans-serif" fill="#111827">{escape(month_label)} 分類圓餅圖</text>',
    ]

    if total > 0:
        angle_start = -math.pi / 2
        for idx, (name, amount) in enumerate(category_totals):
            angle = float(amount / total) * math.tau
            angle_end = angle_start + angle
            x1 = cx + radius * math.cos(angle_start)
            y1 = cy + radius * math.sin(angle_start)
            x2 = cx + radius * math.cos(angle_end)
            y2 = cy + radius * math.sin(angle_end)
            large_arc = 1 if angle > math.pi else 0
            color = colors[idx % len(colors)]
            path = (
                f"M {cx},{cy} "
                f"L {x1:.2f},{y1:.2f} "
                f"A {radius},{radius} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z"
            )
            parts.append(f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
            angle_start = angle_end
    else:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#e5e7eb" stroke="#d1d5db" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="16" font-family="Arial, sans-serif" fill="#6b7280">No data</text>'
        )

    parts.append(
        f'<text x="{cx}" y="{cy + radius + 36}" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" fill="#374151">總計 {escape(format_money(total)) if total > 0 else "NT$0"}</text>'
    )

    for idx, (name, amount) in enumerate(category_totals):
        color = colors[idx % len(colors)]
        pct = (amount / total * Decimal("100")) if total > 0 else Decimal("0")
        y = legend_y + idx * legend_gap
        parts.append(f'<rect x="{legend_x}" y="{y - 14}" width="14" height="14" fill="{color}"/>')
        label = f"{escape(name)}  {escape(format_money(amount))}  {escape(format_percent(pct))}"
        parts.append(
            f'<text x="{legend_x + 22}" y="{y - 2}" font-size="14" font-family="Arial, sans-serif" fill="#111827">{label}</text>'
        )

    parts.append("</svg>")
    write_text(output_path, "\n".join(parts))


def render_mermaid_pie(month_label: str, category_totals: list[tuple[str, Decimal]]) -> str:
    lines = ["```mermaid", "pie showData", f'  title {month_label} 分類占比']
    for name, amount in category_totals:
        lines.append(f'  "{name}" : {decimal_plain(amount)}')
    lines.append("```")
    return "\n".join(lines)


def row_sort_key(row: Row) -> tuple[str, str, str]:
    return (row.date_text, row.source_file.name, row.item)


def render_value(value: Decimal | None) -> str:
    if value is None:
        return "待確認"
    return format_money(value)


def build_monthly_list(
    month_label: str,
    rows: list[Row],
    included_totals: dict[str, Decimal],
    excluded_totals: dict[str, Decimal],
    output_path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# 月報清單")
    lines.append("")
    lines.append(f"期間：`{month_label}`")
    lines.append("")
    lines.append("## 明細")
    lines.append("")

    if rows:
        lines.append("| 日期 | 品項 | 分類 | 數量 | 單價 | 小計 | 備註 | 來源 |")
        lines.append("|------|------|------|------|------|------|------|------|")
        for row in sorted(rows, key=row_sort_key):
            quantity = row.quantity if row.quantity is not None else "待確認"
            lines.append(
                f"| {row.date_text or '待確認'} | {row.item} | {row.category} | "
                f"{quantity} | {render_value(row.unit_price)} | {render_value(row.subtotal)} | "
                f"{row.note or '-'} | {row.source_file.name} |"
            )
    else:
        lines.append("本月沒有記帳明細。")

    lines.append("")
    lines.append("## 分類小計")
    lines.append("")
    category_totals = sorted(included_totals.items(), key=lambda item: (-item[1], item[0]))
    if category_totals:
        lines.append("| 分類 | 金額 |")
        lines.append("|------|------|")
        for category, amount in category_totals:
            lines.append(f"| {category} | {format_money(amount)} |")
        lines.append(f"| 合計 | {format_money(sum(included_totals.values(), Decimal('0')))} |")
    else:
        lines.append("本月沒有可計算的分類小計。")

    if excluded_totals:
        lines.append("")
        lines.append("## 排除項目")
        lines.append("")
        lines.append("| 分類 | 金額 |")
        lines.append("|------|------|")
        for category, amount in sorted(excluded_totals.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {category} | {format_money(amount)} |")
        lines.append(f"| 合計 | {format_money(sum(excluded_totals.values(), Decimal('0')))} |")

    write_text(output_path, "\n".join(lines))


def build_month_report(args: argparse.Namespace) -> Path:
    year, month = normalize_month(args.month)
    root = Path(args.root)
    month_path = month_dir(root, year, month)
    month_path.mkdir(parents=True, exist_ok=True)

    rows = collect_rows(month_path)
    included_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    excluded_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    unresolved_rows: list[Row] = []

    for row in rows:
        if row.subtotal is None:
            unresolved_rows.append(row)
            continue
        if row.category in args.exclude_category:
            excluded_totals[row.category] += row.subtotal
        else:
            included_totals[row.category] += row.subtotal

    sorted_totals = sorted(included_totals.items(), key=lambda item: (-item[1], item[0]))
    included_total = sum((amount for _, amount in sorted_totals), Decimal("0"))
    excluded_total = sum(excluded_totals.values(), Decimal("0"))
    total_for_report = included_total

    summary_path = month_path / "summary.md"
    svg_path = month_path / "summary.svg"
    monthly_list_path = month_path / "monthly-list.md"

    lines: list[str] = []
    lines.append("# 記帳月報")
    lines.append("")
    lines.append(f"期間：`{year:04d}-{month:02d}`")
    lines.append("")

    if sorted_totals:
        lines.append("## 分類清單")
        lines.append("")
        lines.append("| 分類 | 金額 | 占比 |")
        lines.append("|------|------|------|")
        for category, amount in sorted_totals:
            pct = (amount / included_total * Decimal("100")) if included_total > 0 else Decimal("0")
            lines.append(f"| {category} | {format_money(amount)} | {format_percent(pct)} |")
        lines.append(f"| 合計 | {format_money(included_total)} | 100.0% |")
        lines.append("")
    else:
        lines.append("## 分類清單")
        lines.append("")
        lines.append("本月沒有可計算的分類資料。")
        lines.append("")

    if excluded_totals:
        lines.append("## 排除項目")
        lines.append("")
        lines.append("| 分類 | 金額 |")
        lines.append("|------|------|")
        for category, amount in sorted(excluded_totals.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {category} | {format_money(amount)} |")
        lines.append(f"| 合計 | {format_money(excluded_total)} |")
        lines.append("")

    if unresolved_rows:
        lines.append("## 待確認明細")
        lines.append("")
        lines.append("| 來源 | 品項 | 分類 | 數量 | 單價 | 小計 | 備註 |")
        lines.append("|------|------|------|------|------|------|------|")
        for row in unresolved_rows:
            lines.append(
                f"| {row.source_file.name} | {row.item} | {row.category} | "
                f"{row.quantity if row.quantity is not None else '待確認'} | "
                f"{format_money(row.unit_price) if row.unit_price is not None else '待確認'} | "
                f"待確認 | {row.note or '-'} |"
            )
        lines.append("")

    lines.append("## 分析重點")
    lines.append("")
    if sorted_totals:
        top_category, top_amount = sorted_totals[0]
        top_share = (top_amount / included_total * Decimal("100")) if included_total > 0 else Decimal("0")
        lines.append(f"- 最高支出分類是 `{top_category}`，金額 {format_money(top_amount)}，占比 {format_percent(top_share)}。")
        if len(sorted_totals) >= 3:
            top3 = sum(amount for _, amount in sorted_totals[:3])
            top3_share = (top3 / included_total * Decimal("100")) if included_total > 0 else Decimal("0")
            lines.append(f"- 前 3 大分類合計 {format_money(top3)}，占比 {format_percent(top3_share)}。")
        else:
            lines.append(f"- 本月共有 {len(sorted_totals)} 個可計算分類。")
    else:
        lines.append("- 本月沒有可計算的分類資料。")
    if unresolved_rows:
        lines.append(f"- 共有 {len(unresolved_rows)} 筆待確認明細，需要補齊金額後再重算。")
    else:
        lines.append("- 沒有待確認明細。")
    lines.append("")

    lines.append("## 圓餅圖")
    lines.append("")
    lines.append(render_mermaid_pie(f"{year:04d}-{month:02d}", sorted_totals))
    lines.append("")

    if total_for_report > 0:
        lines.append("## 總計")
        lines.append("")
        lines.append("| 項目 | 金額 |")
        lines.append("|------|------|")
        lines.append(f"| 合計 | {format_money(total_for_report)} |")
        lines.append("")

    write_text(summary_path, "\n".join(lines))
    build_svg(f"{year:04d}-{month:02d}", sorted_totals, svg_path)
    build_monthly_list(
        f"{year:04d}-{month:02d}",
        rows,
        included_totals,
        excluded_totals,
        monthly_list_path,
    )

    print(summary_path)
    print(svg_path)
    print(monthly_list_path)
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bookkeeping helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_entry = subparsers.add_parser("new-entry", help="Create a standardized markdown entry")
    new_entry.add_argument("--root", default="bookkeeping", help="Root folder for bookkeeping data")
    new_entry.add_argument("--date", help="Entry date in YYYY-MM-DD; defaults to today")
    new_entry.add_argument("--title", help="Entry title used in the file name")
    new_entry.add_argument("--source", default="manual", help="Source label written into front matter")
    new_entry.add_argument("--overwrite", action="store_true", help="Overwrite an existing file with the same name")

    month_report = subparsers.add_parser("month-report", help="Build a monthly summary")
    month_report.add_argument("--root", default="bookkeeping", help="Root folder for bookkeeping data")
    month_report.add_argument("--month", required=True, help="Target month in YYYY-MM or YYYY/MM")
    month_report.add_argument(
        "--exclude-category",
        action="append",
        default=[],
        help="Category to exclude from the pie chart and included totals",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "new-entry":
        path = create_entry(args)
        print(path)
        return 0
    if args.command == "month-report":
        if not args.exclude_category:
            args.exclude_category = sorted(DEFAULT_EXCLUDED_CATEGORIES)
        build_month_report(args)
        return 0
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
