# Graph Report - auto-upload-tools  (2026-05-04)

## Corpus Check
- 35 files · ~47,382 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 371 nodes · 574 edges · 17 communities detected
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 132 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]

## God Nodes (most connected - your core abstractions)
1. `FeishuDataSource` - 25 edges
2. `NotionDataSource` - 23 edges
3. `TencentVideo` - 21 edges
4. `WeChatVideoUploader` - 16 edges
5. `LocalDataSource` - 16 edges
6. `main()` - 13 edges
7. `main()` - 13 edges
8. `BilibiliVideoUploader` - 13 edges
9. `DouYinVideo` - 13 edges
10. `set_init_script()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `get_data_source()` --calls--> `LocalDataSource`  [INFERRED]
  upload_douyin_videos.py → data_sources/local_data_source.py
- `get_data_source()` --calls--> `NotionDataSource`  [INFERRED]
  upload_douyin_videos.py → data_sources/notion_data_source.py
- `get_data_source()` --calls--> `FeishuDataSource`  [INFERRED]
  upload_douyin_videos.py → data_sources/feishu_data_source.py
- `ensure_login()` --calls--> `douyin_setup()`  [INFERRED]
  upload_douyin_videos.py → uploader/douyin_uploader/main.py
- `upload_single_video()` --calls--> `DouYinVideo`  [INFERRED]
  upload_douyin_videos.py → uploader/douyin_uploader/main.py

## Communities (28 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (30): FeishuDataSource, 获取 tenant_access_token, 查询飞书多维表格记录                  Args:             filter_status: 筛选状态，可以是单个状态字符串或状态列, 从记录中提取字段值（支持所有飞书多维表格字段类型）, 【混合模式】从飞书多维表格读取视频信息，匹配本地视频文件                  此模式下：         1. 从飞书多维表格读取视频元数据（标题, 【统一5阶段模板】处理飞书记录，优先本地视频，无本地则从飞书下载                  阶段1：数据获取 - 从飞书获取记录         阶段2, 从飞书 URL 异步下载文件到临时目录（带重试机制）         自动添加飞书认证头, 批量下载云端视频文件到本地临时目录         【混合模式】优先使用本地 videos/ 文件夹中的文件，没有则从云端下载 (+22 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (32): 【Notion混合模式】优先本地视频，无本地则从Notion云端下载          此模式下：         1. 从 Notion 获取视频元数据（只获, Colors, divider(), empty_state(), get_term_width(), item(), list_item(), print_data_source_header() (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (30): BilibiliVideoUploader, main(), parse_date_range(), 上传视频列表                  Returns:             (成功列表, 失败列表), 解析日期范围字符串          格式: "YYYY-MM-DD,YYYY-MM-DD", 初始化 Bilibili 视频上传管理器                  Args:             mode: 数据源模式 (local/notio, ensure_login(), get_data_source() (+22 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (27): NotionDataSource, 查询 Notion 数据库（带重试机制）                  Args:             filter_obj: 可选的查询过滤器, 解析 Description 字段         格式：多行描述 + 最后一行话题标签, 从页面属性中提取值（支持所有Notion字段类型）, 【混合模式】从 Notion 获取视频信息和文件                  此模式下：         1. 从 Notion 数据库读取所有视频元数据, 在 Notion 记录中查找匹配项                  匹配策略：         1. 精确匹配（去除前后空格）         2. 包含匹配, 获取所有 Notion 云端视频记录（不依赖本地视频文件）                  用于视频预览页面的"云端"模式，直接显示所有 Notion 数据库, 从配置中获取数据库ID         优先级：notion_database_id > notion_database_name（通过API查找） (+19 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (26): DouYinVideo, 抖音视频上传类          封装抖音创作者中心的视频上传流程, 初始化抖音视频上传实例                  Args:             title: 视频标题（30字以内）             fi, 设置定时发布时间          步骤：         1. 点击"定时发布"选项         2. 点击日期输入框打开日历弹窗         3., 设置封面（抖音需要同时设置竖封面 3:4 和横封面 4:3）                  支持两种模式：         1. 单封面模式：从一张图裁剪出, 设置地理位置                  Args:             page: Playwright Page 对象, 添加视频到合集                  抖音合集区域有两个下拉框：         1. 合集类型下拉框 (.select-mix-type-G9iq, 设置同步到头条/西瓜视频                  Args:             page: Playwright Page 对象 (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (23): open_browser(), 抖音视频号上传器  提供抖音创作者中心的视频上传功能，支持： - Cookie 验证与生成 - 视频上传 - 定时发布 - 封面上传 - 地理位置设置 - 同步, cookie_auth(), douyin_cookie_gen(), douyin_setup(), 抖音上传器初始化          检查 Cookie 有效性，如失效则引导用户重新登录          Args:         account_file, 验证 Cookie 是否有效          Args:         account_file: Cookie 文件路径              Ret, 生成抖音登录 Cookie          打开浏览器让用户扫码登录，登录后保存 Cookie          Args:         account_ (+15 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (13): ABC, 数据源抽象基类模块 支持本地 txt 和 Notion 云端两种数据源, 【公共方法】异步下载文件                  Args:             url: 文件URL             filename:, 【公共方法】批量下载云端视频文件到本地临时目录         【混合模式】优先使用本地 videos/ 文件夹中的文件，没有则从云端下载, VideoDataSource, VideoInfo, 飞书多维表格数据源实现 从飞书Bitable获取视频信息和文件，支持混合模式（优先本地，无本地则从云端下载）, LocalDataSource (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (19): bilibili_setup(), BilibiliVideo, BilibiliVideoUploader, cookie_auth(), ensure_login(), extract_keys_from_json(), get_bilibili_cookie(), Bilibili 视频上传器 - Playwright 浏览器自动化方式 (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (7): object, 设置视频位置                  Args:             page: Playwright 页面对象, 兼容旧方法，调用 set_location, 在视频上传期间填写表单（封面除外）                  此方法与 detect_upload_status 并行执行，充分利用上传等待时间, 检测视频上传和处理状态          对于大视频，仅检测"发表"按钮不可靠，需要额外检测视频封面预览是否就绪, 添加视频到合集                  流程：         1. 点击"选择合集"弹出下拉框         2. 加载合集列表, TencentVideo

### Community 9 - "Community 9"
Cohesion: 0.17
Nodes (8): 加载配置，优先读取 config.json，不存在则读取 config.example.json, 获取视频文件夹中的视频、标题和封面信息，使用智能匹配选择视频, 获取按日期排序的视频文件夹，无日期的使用config中的默认日期, 统一的单视频上传方法                  Args:             video_data: 视频数据字典，包含 title, descr, 将视频移动到 published 目录                  Args:             video_path: 视频文件路径, 清理混合模式的临时文件                  规范做法：         - 临时文件在上传成功后直接删除（源文件在 Notion/飞书）, 从数据源上传视频（混合模式）                  Returns:             dict: {'success': [成功视频列表],, WeChatVideoUploader

### Community 10 - "Community 10"
Cohesion: 0.2
Nodes (9): download_file_async(), generate_cover_filename(), generate_filename_from_url(), generate_video_filename(), 文件下载工具模块 提供通用的异步文件下载功能，支持重试机制和进度回调, 从 URL 生成文件名          Args:         url: 文件URL         name_for_match: 用于匹配的名称, 生成视频文件名          Args:         name_for_match: 用于匹配的名称         publish_date: 发布日, 生成封面文件名          Args:         name_for_match: 用于匹配的名称         publish_date: 发布日 (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.4
Nodes (4): create_logger(), log_formatter(), Create custom logger for different business modules.     :param str log_name: na, Formatter for log records.     :param dict record: Log object containing log met

## Knowledge Gaps
- **135 isolated node(s):** `上传单个视频到抖音      Args:         video: 视频信息对象         account_file: Cookie 文件路径`, `批量上传视频          Args:         videos: 视频信息列表         account_file: Cookie 文件路径`, `更新视频发布状态到数据源          Args:         data_source: 数据源实例         result: 上传结果 {'su`, `统一更新视频发布状态（公共函数）          Args:         data_source: 数据源对象（NotionDataSource 或 Fe`, `加载配置，优先读取 config.json，不存在则读取 config.example.json` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WeChatVideoUploader` connect `Community 9` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Why does `FeishuDataSource` connect `Community 0` to `Community 9`, `Community 2`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Why does `NotionDataSource` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 6`, `Community 9`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `FeishuDataSource` (e.g. with `WeChatVideoUploader` and `BilibiliVideoUploader`) actually correct?**
  _`FeishuDataSource` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `NotionDataSource` (e.g. with `WeChatVideoUploader` and `BilibiliVideoUploader`) actually correct?**
  _`NotionDataSource` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `TencentVideo` (e.g. with `WeChatVideoUploader` and `._upload_single_video()`) actually correct?**
  _`TencentVideo` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WeChatVideoUploader` (e.g. with `TencentVideo` and `VideoInfo`) actually correct?**
  _`WeChatVideoUploader` has 5 INFERRED edges - model-reasoned connections that need verification._