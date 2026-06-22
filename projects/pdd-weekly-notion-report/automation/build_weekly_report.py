#!/usr/bin/env python3
"""Build a dry-run PDD weekly report from a CSV export."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = {
    "date",
    "shop_name",
    "product_name",
    "sku",
    "visitors",
    "orders",
    "revenue",
    "refund_amount",
    "ad_spend",
}


@dataclass
class Totals:
    visitors: float = 0.0
    orders: float = 0.0
    revenue: float = 0.0
    refund_amount: float = 0.0
    ad_spend: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a local dry-run PDD weekly report from a CSV file."
    )
    parser.add_argument("--input", required=True, help="Path to the PDD CSV export.")
    parser.add_argument("--week", required=True, help="Report week, for example 2026-W26.")
    parser.add_argument("--shop", help="Optional shop name override.")
    parser.add_argument(
        "--output",
        help="Markdown output path. Defaults to data/output/pdd_weekly_<week>.md.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="CSV file encoding. Defaults to utf-8-sig.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required for the current MVP. Generates local preview only.",
    )
    return parser.parse_args()


def parse_number(value: str | None, *, row_number: int, column: str, warnings: list[str]) -> float:
    if value is None or str(value).strip() == "":
        warnings.append(f"第 {row_number} 行 `{column}` 为空，按 0 处理。")
        return 0.0

    text = str(value).strip().replace(",", "")
    text = re.sub(r"^[￥¥$]", "", text)
    if text.endswith("%"):
        text = text[:-1]

    try:
        return float(text)
    except ValueError:
        warnings.append(f"第 {row_number} 行 `{column}` 无法识别为数字：{value!r}，按 0 处理。")
        return 0.0


def pct(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return "N/A"
    return f"{numerator / denominator:.2%}"


def ratio(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return "N/A"
    return f"{numerator / denominator:.2f}"


def money(value: float) -> str:
    return f"¥{value:,.2f}"


def whole(value: float) -> str:
    return f"{value:,.0f}"


def read_rows(input_path: Path, encoding: str) -> tuple[list[dict[str, str]], list[str]]:
    warnings: list[str] = []
    with input_path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit("输入 CSV 没有表头。")

        columns = {name.strip() for name in reader.fieldnames}
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise SystemExit(f"输入 CSV 缺少必要列：{', '.join(missing)}")

        rows = []
        for row_number, row in enumerate(reader, start=2):
            clean_row = {str(key).strip(): (value or "").strip() for key, value in row.items()}
            if not any(clean_row.values()):
                warnings.append(f"第 {row_number} 行为空，已跳过。")
                continue
            rows.append(clean_row)

    if not rows:
        raise SystemExit("输入 CSV 没有可处理的数据行。")

    return rows, warnings


def aggregate(rows: Iterable[dict[str, str]], warnings: list[str]) -> tuple[Totals, dict[tuple[str, str], Totals], set[str], list[str]]:
    totals = Totals()
    by_product: dict[tuple[str, str], Totals] = defaultdict(Totals)
    shops: set[str] = set()
    dates: list[str] = []

    for index, row in enumerate(rows, start=2):
        shop_name = row["shop_name"].strip()
        product_name = row["product_name"].strip()
        sku = row["sku"].strip()
        date_value = row["date"].strip()

        if shop_name:
            shops.add(shop_name)
        else:
            warnings.append(f"第 {index} 行 `shop_name` 为空。")

        if not product_name:
            warnings.append(f"第 {index} 行 `product_name` 为空。")
            product_name = "未命名商品"
        if not sku:
            warnings.append(f"第 {index} 行 `sku` 为空。")
            sku = "unknown-sku"
        if date_value:
            dates.append(date_value)
        else:
            warnings.append(f"第 {index} 行 `date` 为空。")

        values = Totals(
            visitors=parse_number(row.get("visitors"), row_number=index, column="visitors", warnings=warnings),
            orders=parse_number(row.get("orders"), row_number=index, column="orders", warnings=warnings),
            revenue=parse_number(row.get("revenue"), row_number=index, column="revenue", warnings=warnings),
            refund_amount=parse_number(row.get("refund_amount"), row_number=index, column="refund_amount", warnings=warnings),
            ad_spend=parse_number(row.get("ad_spend"), row_number=index, column="ad_spend", warnings=warnings),
        )

        for column_name, value in vars(values).items():
            if value < 0:
                warnings.append(f"第 {index} 行 `{column_name}` 为负数，请确认。")

        totals.visitors += values.visitors
        totals.orders += values.orders
        totals.revenue += values.revenue
        totals.refund_amount += values.refund_amount
        totals.ad_spend += values.ad_spend

        product_totals = by_product[(product_name, sku)]
        product_totals.visitors += values.visitors
        product_totals.orders += values.orders
        product_totals.revenue += values.revenue
        product_totals.refund_amount += values.refund_amount
        product_totals.ad_spend += values.ad_spend

    return totals, by_product, shops, dates


def render_report(
    *,
    week: str,
    shop: str,
    totals: Totals,
    by_product: dict[tuple[str, str], Totals],
    dates: list[str],
    warnings: list[str],
    source: Path,
) -> str:
    title = f"拼多多周报 {week}"
    date_range = "N/A"
    if dates:
        date_range = f"{min(dates)} 至 {max(dates)}"

    top_products = sorted(by_product.items(), key=lambda item: item[1].revenue, reverse=True)[:5]

    lines = [
        f"# {title}",
        "",
        "## 基本信息",
        "",
        f"- 店铺：{shop}",
        f"- 周期：{week}",
        f"- 日期范围：{date_range}",
        f"- 数据源：`{source}`",
        "",
        "## 核心指标",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 销售额 | {money(totals.revenue)} |",
        f"| 订单数 | {whole(totals.orders)} |",
        f"| 访客数 | {whole(totals.visitors)} |",
        f"| 转化率 | {pct(totals.orders, totals.visitors)} |",
        f"| 退款金额 | {money(totals.refund_amount)} |",
        f"| 退款率 | {pct(totals.refund_amount, totals.revenue)} |",
        f"| 推广花费 | {money(totals.ad_spend)} |",
        f"| 推广 ROI | {ratio(totals.revenue, totals.ad_spend)} |",
        "",
        "## TOP 商品",
        "",
        "| 排名 | 商品 | SKU | 销售额 | 订单数 | 访客数 | 转化率 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]

    for rank, ((product_name, sku), product_totals) in enumerate(top_products, start=1):
        lines.append(
            f"| {rank} | {product_name} | {sku} | {money(product_totals.revenue)} | "
            f"{whole(product_totals.orders)} | {whole(product_totals.visitors)} | "
            f"{pct(product_totals.orders, product_totals.visitors)} |"
        )

    lines.extend(
        [
            "",
            "## 本周摘要",
            "",
            f"- 本周销售额 {money(totals.revenue)}，订单数 {whole(totals.orders)}，整体转化率 {pct(totals.orders, totals.visitors)}。",
            f"- 推广花费 {money(totals.ad_spend)}，推广 ROI {ratio(totals.revenue, totals.ad_spend)}。",
            f"- 退款金额 {money(totals.refund_amount)}，退款率 {pct(totals.refund_amount, totals.revenue)}。",
            "",
            "## 下周动作",
            "",
            "- 复核 TOP 商品库存、价格和素材。",
            "- 关注低转化商品的标题、主图和活动承接。",
            "- 对推广 ROI 偏低的计划做预算和关键词检查。",
            "",
            "## 数据检查",
            "",
        ]
    )

    if warnings:
        lines.append("| 级别 | 内容 |")
        lines.append("| --- | --- |")
        for warning in warnings[:30]:
            lines.append(f"| warning | {warning} |")
        if len(warnings) > 30:
            lines.append(f"| warning | 还有 {len(warnings) - 30} 条检查信息未展示。 |")
    else:
        lines.append("- 未发现缺失字段或异常数值。")

    lines.append("")
    return "\n".join(lines)


def find_project_root(input_path: Path) -> Path:
    for candidate in [input_path.resolve().parent, *input_path.resolve().parents, Path.cwd().resolve()]:
        if (candidate / "automation").exists() and (candidate / "data").exists():
            return candidate
    return Path.cwd()


def default_output_path(input_path: Path, week: str) -> Path:
    return find_project_root(input_path) / "data" / "output" / f"pdd_weekly_{week}.md"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()
    if not args.dry_run:
        print("当前 MVP 只允许 dry-run。请添加 `--dry-run` 后再运行。", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"输入文件不存在：{input_path}", file=sys.stderr)
        return 2

    rows, warnings = read_rows(input_path, args.encoding)
    totals, by_product, shops, dates = aggregate(rows, warnings)

    if args.shop:
        shop = args.shop
    elif len(shops) == 1:
        shop = next(iter(shops))
    elif shops:
        shop = "多个店铺：" + "、".join(sorted(shops))
    else:
        shop = "未识别店铺"

    output_path = Path(args.output) if args.output else default_output_path(input_path, args.week)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = render_report(
        week=args.week,
        shop=shop,
        totals=totals,
        by_product=by_product,
        dates=dates,
        warnings=warnings,
        source=input_path,
    )
    output_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nDry-run completed. Markdown report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
