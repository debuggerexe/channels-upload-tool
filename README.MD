# 微信视频号自动上传工具

自动化发布视频到微信视频号平台，支持本地和 Notion 云端两种数据源模式。

## 功能特性

- **双数据源模式**
  - 本地模式：从 `videos/` 文件夹读取 txt 文件获取标题/标签
  - 云端模式：从 Notion 数据库读取视频元数据，本地只存视频文件

- **智能处理**
  - 智能文件名匹配（自动去除日期前缀）
  - 短标题自动清理（过滤微信不支持的特殊字符，**超过16字自动截断**）
  - 封面智能裁剪（高图自动裁剪为3:4比例）
  - 自动声明原创
  - **自动添加合集（匹配成功才添加）**
  - **并行上传优化（上传期间填写表单，节省时间）**

- **批量上传**
  - 按发布日期自动排序
  - 失败自动重试
  - 上传成功后自动归档到 `published/` 目录

---

## 快速开始

```bash
source .venv/bin/activate && python upload_wechat_videos.py
```

运行后选择数据源模式：
1. **本地模式** - 从 `videos/` 读取 txt 文件获取标题/标签
2. **云端模式** - 从 Notion 读取元数据

### 上传流程优化

工具采用**并行处理**策略节省上传时间：

1. **开始上传** - 选择视频文件开始上传
2. **并行处理** - 视频上传期间自动填写：
   - 标题和话题
   - 短标题
   - 合集选择
   - 原创声明
   - 位置设置（不显示位置）
3. **封面处理** - 视频上传完成后处理封面（必须等视频解析完成）
4. **发布/保存** - 点击发表或保存草稿

此优化充分利用视频上传的等待时间，大幅提升批量上传效率。

---

## 新机器初始化

首次在新机器上运行：

```bash
# 1. 克隆项目
git clone https://github.com/debuggerexe/channels-upload-tool.git
cd channels-upload-tool

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
playwright install

# 4. 复制配置文件（必须步骤）
cp config.example.json config.json
# 根据需要编辑 config.json
```

**首次运行（获取 Cookie）：**

```bash
source .venv/bin/activate && python upload_wechat_videos.py
```

会弹出二维码扫码登录，登录成功后 cookie 自动保存，程序会继续执行上传流程。

**之后每次运行：**

```bash
source .venv/bin/activate && python upload_wechat_videos.py
```

Cookie 已保存，直接开始上传，无需再次扫码。

---

### 本地模式发布方式

选择本地模式后，会提示选择操作：

1. **定时发布** - 确认并开始上传，按设置的发布时间发表视频
2. **保存草稿** - 确认并开始上传，仅保存到草稿箱
3. **取消上传** - 退出程序

---

### 云端模式发布方式

选择云端模式后，会提示选择发布方式：

1. **定时发布** - 按设置的发布时间发表视频
2. **保存草稿** - 仅保存到草稿箱，不发表
3. **退出** - 取消上传

---

## 本地模式

### 目录结构

```
videos/
├── 260101_video1/
│   ├── video1.mp4          # 视频文件
│   ├── video1.txt          # 标题和描述（可选）
│   └── cover1.jpg          # 封面图（可选）
└── 260102_video2/
    ├── video2.mp4
    ├── video2.txt
    └── cover2.jpg
```

### txt 文件格式

在视频文件夹中创建与视频同名的 `.txt` 文件（如 `video1.txt`），格式如下：

```
视频短标题（第一行）
视频描述内容...
#话题标签1 #话题标签2
```

**填写要求：**

| 行 | 内容 | 必填 | 说明 |
|---|---|---|---|
| 第1行 | 短标题 | ✅ | 视频号顶部显示的短标题，**只保留中文字符** |
| 第2-N行 | 描述 | 可选 | 视频描述区内容，支持多行 |
| 最后1行 | 标签 | 可选 | 以 `#` 开头的话题标签 |

**短标题处理规则：**
- 只保留中文字符（自动去掉英文、数字、符号）
- 不足6字自动补空格
- **超过16字强行截断**（直接取前16字）

**描述区格式：**

视频号描述区最终内容 = `标题 + 换行 + 描述 + 换行 + 标签`

- 如果描述最后一行已有以 `#` 开头的标签，不再追加标签
- 如果没有标签，仅显示短标题和描述

---

## 云端模式（Notion）

### 数据库字段

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `短标题` | `Title` | 视频号短标题（16字以内），同时用于匹配本地视频文件名/文件夹名 | ✅ |
| `标题` | `Rich Text` | 视频号主标题（显示在视频下方） | 可选 |
| `描述` | `Rich Text` | 视频描述区内容 | 可选 |
| `标签` | `Rich Text` | 话题标签（如 `#话题1 #话题2`） | 可选 |
| `合集` | `Multi-select` | 视频合集名称列表（可多选） | 可选 |
| `发布日期` | `Date` | 发布日期 | ✅ |

**字段说明：**
- **短标题**：视频号顶部显示的短标题（16字以内），同时用于匹配本地视频文件
  - 只保留中文字符（自动去掉英文、数字、符号）
  - 不足6字自动补空格
  - 超过16字**强行截断**（直接取前16字，不保留完整词义）
- **标题**：视频下方显示的主标题
- **描述**：视频描述区内容
- **标签**：话题标签，会自动追加到描述区后面
- **合集**：视频合集名称列表（支持多选）
  - Notion 中使用 `Multi-select` 类型，可添加多个合集
  - 上传时自动点击"选择合集"按钮
  - **匹配规则**：Notion 中的任意合集名称与视频号平台的任意合集**完全匹配**即可自动选择
  - 全部未匹配到会提示在视频号后台手动创建
- **发布日期**：发布日期，可只填日期（用 `publish_times` 作为时间）或完整时间

**视频号描述区格式：**

格式：`标题 + 换行 + 描述 + 换行 + 标签`

| 部分 | 来源字段 | 说明 |
|------|----------|------|
| 标题 | `标题` 字段 | 视频号主标题，显示在描述区第一行 |
| 描述 | `描述` 字段 | 视频详细描述内容 |
| 标签 | `标签` 字段 | 以 `#` 开头的话题标签 |

**标签去重逻辑：**
- 如果**描述字段的最后一行以 # 开头**（表示已包含话题标签），则不再追加标签字段
- 如果描述字段中没有标签行，且有标签字段，则将标签追加到描述后面

**示例1（描述已含标签）：**
```
标题: "啊啊啊"
描述: "啊啊啊啊啊...\n#标签1 #标签2"
标签: "#标签1 #标签2"
```
→ 最终描述区内容：
```
啊啊啊
啊啊啊啊啊...
#标签1 #标签2
```
（标签字段被忽略，因为描述中已有标签）

**示例2（描述不含标签）：**
```
标题: "啊啊啊"
描述: "啊啊啊啊啊..."
标签: "#标签1 #标签2"
```
→ 最终描述区内容：
```
啊啊啊
啊啊啊啊啊...
#标签1 #标签2
```

### 视频存放方式

**方式一：子文件夹形式（推荐）**
```
videos/
├── 260101_video1/
│   ├── video1.mp4
│   └── cover1.jpg
└── 260102_video2/
    ├── video2.mp4
    └── cover2.jpg
```

**方式二：直接存放**
```
videos/
├── 260101_video1.mp4
├── 260101_video1.jpg
├── 260102_video2.mp4
└── 260102_video2.jpg
```

### 环境变量

```bash
export NOTION_API_TOKEN='your_token'
```

---

## 配置说明

**配置文件优先级：**
1. `config.json` - 本地配置文件（优先读取）
2. `config.example.json` - 默认配置模板（随仓库提供）

**首次使用：**

```bash
# 复制示例配置文件
cp config.example.json config.json

# 根据需要编辑配置
nano config.json
```

**config.json 示例：**

```json
{
  "publish_date": "2026-01-01",
  "publish_times": ["10:00"],
  "original_declaration": true,
  "cover_position": "top",
  "collection": ""
}
```

**配置项说明：**

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `publish_date` | string | "2026-01-01" | 默认发布日期，格式：YYYY-MM-DD，无日期前缀的文件夹使用 |
| `publish_times` | array | ["10:00"] | 每日发布时间，可设多个时段如 ["10:00", "14:00"] |
| `timezone` | string | "Asia/Shanghai" | 时区设置 |
| `video_dir` | string | "videos" | 视频文件夹路径 |
| `text_dir` | string | "texts" | 文本文件夹路径 |
| `original_declaration` | boolean | true | 是否自动声明原创：true / false |
| `cover_position` | string | "top" | 封面裁剪位置：top(顶部) / middle(中间) / bottom(底部) |
| `collection` | string | "" | 默认合集名称，留空则不添加，支持逗号分隔多个 |
| `notion_database_id` | string | "" | Notion数据库ID（云端模式可选） |
| `notion_database_name` | string | "" | Notion数据库名称（云端模式可选） |

完整配置字段见 `config.example.json`

---

## 手动上传（调试用）

```bash
python open_browser.py
```

打开已登录的浏览器，可手动操作上传。

---

## Cookie 获取

首次使用需获取登录凭证：

```bash
python examples/get_tencent_cookie.py
```

扫码登录后会自动保存到 `cookies/tencent_uploader/account.json`

---

## 代码架构优化

### 统一上传流程

**重构前的问题：**
- 本地模式和云端模式有 100+ 行重复代码
- 上传逻辑分散在两个方法中
- 维护困难，容易遗漏功能同步

**重构后的结构：**

```python
# 公共方法（统一处理）
_upload_single_video()     # 单视频上传（含重试、封面处理）
_move_to_published()       # 文件归档到 published 目录

# 模式入口（仅数据组装和流程控制）
upload_all_videos()        # 本地模式 → 调用公共方法
upload_videos_from_source() # 云端模式 → 调用公共方法
```

**优化收益：**
- 代码量减少约 60%
- 两种模式功能完全一致（发布方式、短标题截断、封面处理）
- 维护简单，只需修改一处即可同步到两种模式

### 封面处理优化

**问题：** 视频上传完成后，封面预览元素可能还未就绪，导致封面处理失败。

**解决：** 添加封面预览等待逻辑，最多等待 10 秒确保封面元素加载完成后再处理。

---

## 项目结构

```
├── data_sources/           # 数据源模块
│   ├── data_source.py      # 抽象基类
│   ├── local_data_source.py  # 本地实现
│   └── notion_data_source.py # Notion 实现
├── uploader/
│   └── tencent_uploader/   # 微信视频号上传器
│       └── main.py
├── utils/                  # 工具模块
│   ├── cover_cropper.py    # 封面裁剪
│   ├── files_times.py      # 文件读取、时间处理
│   └── log.py              # 日志
├── videos/                 # 视频文件夹
├── published/              # 已上传视频归档
├── upload_wechat_videos.py # 批量上传主程序
├── open_browser.py         # 手动上传工具
├── config.example.json     # 配置模板（复制为 config.json 后修改）
└── config.json            # 本地配置文件（不上传 GitHub）
```

---

## 依赖安装

```bash
pip install -r requirements.txt
playwright install
```

---

## 日志

日志文件保存在 `logs/tencent.log`
