# JATS2PDF — JATS XML 转 PDF 自动化转换器

**学术期刊结构化技术创新大赛 — 选题二：JATS XML → PDF 自动化映射与生成**

将 JATS (Journal Article Tag Suite) XML 学术论文自动转换为排版规范的 PDF 文档，
支持双栏布局、图表渲染、数学公式处理、参考文献格式化等完整学术出版流程。

## 运行环境要求

- **Python 3.9+**
- Windows / Linux / macOS 均可运行
- 无需安装 GTK3（使用 Playwright/Edge 后端）

## 快速开始（5 分钟搭建）

以下命令在 **项目根目录 `jats2pdf/`** 下执行：

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 Chromium 浏览器（Playwright 后端需要，一次性）
playwright install chromium

# 3. 运行示例（生成 PDF）
python run.py "..\样例-最新版\样例-最新版\样例1\第二组\初始文件.xml" -o output/sample1.pdf -v
```

转换完成后，PDF 和中间 HTML 文件均输出到 `output/` 目录。

> **备选后端**：如果系统安装了 GTK3 运行库，会自动使用 WeasyPrint（最佳排版质量）。
> Windows 用户推荐使用 Playwright 后端（无需额外安装 GTK3）。

## 命令行用法

```bash
# 基本用法
python run.py <XML文件路径>

# 指定输出路径
python run.py article.xml -o output.pdf

# 指定图片目录（如果 XML 同目录下没有 figures/ 等子目录）
python run.py article.xml -f ./figures_extracted/

# 仅生成 HTML 预览
python run.py article.xml --html-only

# 详细输出
python run.py article.xml -v
```

## 测试样例

项目提供了 5 组标准测试样例及 5 组补充样例，位于 `..\样例-最新版\` 目录。

```bash
# 批量测试 5 组主样例
python batch_test.py
```

每组样例包含：
- `初始文件.xml` — JATS XML 输入
- `最终文件.pdf` — 参考输出（用于对照）
- `figures.zip` 或 `figure.zip` — 图片资源（程序自动解压）

## 核心功能

| 功能 | 实现 |
|------|------|
| **双栏排版** | CSS column-count 实现，标题/摘要单栏、正文双栏 |
| **表格渲染** | 三线表学术风格，支持 colspan/rowspan，超宽表自动横排 |
| **图片嵌入** | 自动查找、压缩（≤1600px）、Base64 内嵌，支持模糊文件名匹配 |
| **公式渲染** | MathML → Unicode/HTML 转换，支持分式、上下标、希腊字母 |
| **参考文献** | 支持 `<element-citation>` 和 `<mixed-citation>` 两种格式，Vancouver 风格 |
| **ORCID 链接** | 作者名后绿色 `ID` 圆点，点击跳转 ORCID 页面 |
| **交叉引用** | 正文中 `[1]`、`Table 1`、`Fig. 1` 等蓝色可点击引用 |
| **多后端** | WeasyPrint（最优）/ Playwright Chromium / xhtml2pdf 自动选择 |

## 技术架构

```
JATS XML
  └─ lxml 解析 ──→ Python dataclass 数据模型
                      └─ Jinja2 模板渲染 ──→ HTML（含内嵌 CSS + base64 图片）
                                            └─ Playwright/WeasyPrint ──→ PDF
```

- **解析层**：lxml + XPath，支持 JATS 1.3 Publishing DTD
- **数据层**：Python dataclasses，类型安全
- **渲染层**：Jinja2 模板引擎 + CSS Paged Media
- **输出层**：Playwright Chromium（主）/ WeasyPrint / xhtml2pdf

## 项目结构

```
jats2pdf/
├── jats2pdf/              # 核心包
│   ├── parser.py          # JATS XML 解析器
│   ├── models.py          # 数据模型
│   ├── renderer.py        # 多后端 PDF 渲染器
│   ├── math_handler.py    # MathML 转换器
│   ├── figure_resolver.py # 图片查找与压缩
│   ├── utils.py           # 工具函数
│   ├── cli.py             # 命令行入口
│   └── templates/         # Jinja2 模板 + CSS
├── tests/                 # 测试用例
├── output/                # 输出目录
├── run.py                 # 启动入口
├── batch_test.py          # 批量测试脚本
├── requirements.txt       # 依赖清单
├── setup.py               # 包配置
├── README.md              # 本文件
└── 技术方案说明书.md        # 技术方案文档
```

## License

本项目为 IMR 学术期刊结构化技术创新大赛参赛作品。
