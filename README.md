# QuoteHub

中国互联网创业者语录合集 —— 将 PDF 原始资料转换为结构化 Markdown，方便阅读、搜索与引用。

## 内容

| 人物 | 来源 | 条目数 | 图片数 |
|------|------|--------|--------|
| [王兴](./wang-xing/quotes.md) | 饭否动态合集（2007–2020年12月） | 15,420 条 | 1,304 张 |
| [张一鸣](./zhang-yi-ming/quotes.md) | 微博语录精选（近10年） | 231 条 | — |

## 项目结构

```
QuoteHub/
├── scripts/
│   ├── convert.sh          # 主入口：一键提取图片 + 生成 Markdown
│   ├── extract_images.py   # 从 PDF 中提取图片，建立编号映射
│   └── format.py           # 将 pdftotext 原始文本格式化为 Markdown
├── wang-xing/
│   ├── quotes.md           # 生成的语录 Markdown
│   ├── images/             # 提取的图片（Git LFS）
│   │   ├── map.json        # 图片编号映射表
│   │   └── entry_*.jpeg    # 各条目图片
│   └── *.pdf               # 原始 PDF（不提交，见 .gitignore）
├── zhang-yi-ming/
│   ├── quotes.md           # 生成的语录 Markdown
│   └── *.pdf               # 原始 PDF（不提交）
├── .gitattributes          # Git LFS 配置（images/*.jpeg）
├── .gitignore              # 忽略 PDF 和系统文件
└── README.md
```

## 使用说明

### 环境要求

```bash
# macOS（使用 Homebrew）
brew install poppler          # 提供 pdftotext

# Python 依赖
pip3 install pymupdf          # 提供图片提取能力
```

### 生成 Markdown

将 PDF 放入对应的子目录（`wang-xing/` 或 `zhang-yi-ming/`），然后运行：

```bash
bash scripts/convert.sh
```

该命令会依次执行：

1. **提取图片**（`extract_images.py`）——扫描王兴 PDF 的全部 2,284 页，将 1,304 张图片保存到 `wang-xing/images/`，并生成 `map.json` 编号映射
2. **生成王兴语录**（`format.py`）——调用 `pdftotext` 提取文本，格式化为带时间戳和图片引用的 Markdown
3. **生成张一鸣语录**（`format.py`）——提取文本，按主题分节，修复 CJK 字间距
4. **更新 README**——自动写入目录索引

### 仅重新提取图片

```bash
python3 scripts/extract_images.py
```

### 添加新人物

1. 在项目根目录新建子文件夹，放入 PDF
2. 在 `scripts/convert.sh` 末尾仿照现有格式添加 `convert_pdf` 调用
3. 在 `scripts/format.py` 中为该人物实现对应的 `format_xxx()` 函数
4. 运行 `bash scripts/convert.sh`

## 格式说明

**王兴（饭否）**：每条动态为独立的 `### N` 节，包含正文、转发链、图片（如有）和发布时间。

```markdown
### 88

在出机场的高速上看到一个很鸡血的广告大牌：Every success begins with a big dream!
看了落款才知道这是一个床垫广告-_-!

*2020-01-31 13:39 · 手机上网*
```

**张一鸣（微博）**：按主题分为三个 `##` 节，每条语录为 `### 001` 格式。

```markdown
## 01 关于成长

### 001

人常会不自觉地记下对自己有利的部分，这是形成委屈的重要原因。
```

---

_`wang-xing/quotes.md` 和 `README.md` 由 `scripts/convert.sh` 自动生成，请勿直接编辑。_
