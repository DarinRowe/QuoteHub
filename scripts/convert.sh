#!/usr/bin/env bash
# Convert PDFs in this project to Markdown and generate a README index.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# -------------------------------------------------------------------
# Convert one PDF to Markdown
#   $1 = subfolder key  $2 = display name  $3 = PDF title  $4 = PDF filename
# -------------------------------------------------------------------
convert_pdf() {
  local key="$1"
  local display="$2"
  local title="$3"
  local pdf_file="$4"

  local dir="$ROOT/$key"
  local pdf="$dir/$pdf_file"
  local out="$dir/quotes.md"

  if [ ! -f "$pdf" ]; then
    echo "  [SKIP] PDF not found: $pdf"
    return
  fi

  echo "  Converting: $pdf"

  {
    echo "# ${title}"
    echo ""
    echo "> 来源：${pdf_file}"
    echo ""
    echo "---"
    echo ""

    # Extract text and pipe through Python formatter for clean Markdown
    pdftotext -nopgbrk -enc UTF-8 "$pdf" - \
      | sed 's/[[:space:]]*$//' \
      | python3 "$SCRIPTS_DIR/format.py" "$key"
  } > "$out"

  local lines
  lines="$(wc -l < "$out")"
  echo "  Written: $out  (${lines} lines)"
}

# -------------------------------------------------------------------
# Generate README with directory index
# -------------------------------------------------------------------
generate_readme() {
  local readme="$ROOT/README.md"

  cat > "$readme" <<'HEADER'
# QuoteHub

中国互联网创业者语录合集。

## 目录

HEADER

  # Wang Xing entry
  cat >> "$readme" <<'WX'
### 王兴

- 文集：**王兴饭否动态合集（2007–2020年12月）**
- 言论记录：[wang-xing/quotes.md](./wang-xing/quotes.md)

WX

  # Zhang Yiming entry
  cat >> "$readme" <<'ZYM'
### 张一鸣

- 文集：**张一鸣近10年的微博**
- 言论记录：[zhang-yi-ming/quotes.md](./zhang-yi-ming/quotes.md)

ZYM

  echo "---" >> "$readme"
  echo "" >> "$readme"
  echo "_由 \`convert.sh\` 自动生成于 $(date '+%Y-%m-%d')_" >> "$readme"

  echo "README written: $readme"
}

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
echo "=== QuoteHub PDF → Markdown converter ==="
echo ""

echo "[wang-xing] Extracting images..."
python3 "$SCRIPTS_DIR/extract_images.py"
echo ""

echo "[wang-xing]"
convert_pdf \
  "wang-xing" \
  "王兴" \
  "王兴饭否动态合集（2007–2020年12月）" \
  "88万字，王兴饭否动态合集，2007年-2020年12月.pdf"
echo ""

echo "[zhang-yi-ming]"
convert_pdf \
  "zhang-yi-ming" \
  "张一鸣" \
  "张一鸣近10年的微博" \
  "张一鸣近10年的微博 (张一鸣) (z-lib.org).pdf"
echo ""

generate_readme
echo ""
echo "Done."
