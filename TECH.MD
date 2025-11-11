# 技术说明（TECH.md）

## 1. 项目目标
- 复现猫咪 VIP 站点的账号登录、分类查询与视频列表接口，为协议爬虫/逆向分析提供示例。
- 提供命令行 (`maomi_spider.py`) 与 Web 控制台 (`web_app.py`) 两种交互方式，方便调试、展示与交流学习。
- 不包含、也不提供任何真实账号信息或下载链路，默认场景为本地研究。

## 2. 依赖环境
- Python 3.11+
- `requests`：所有协议请求
- `pycryptodome`：AES-CBC 加解密
- `flask`：Web 控制台（可选）

示例安装：
```bash
pip install requests pycryptodome flask
```

## 3. 登录协议逆向
| 项 | 说明 |
| --- | --- |
| 登录接口 | `POST https://bmapi.jxychy.com/api/user/loginByUsername` |
| 负载字段 | `encode_sign`（MD5）、`post-data`（AES-CBC Base64）、`suffix`、`timestamp` 等 |
| AES Key/IV | 脚本内常量，IV 需拼接 `suffix` 后截取 16 字节 |
| 加签逻辑 | 将 payload key/value 排序 → `key=value&` 拼接 → 末尾追加 `SIGN_KEY` → MD5 → 小写十六进制 |
| 加密流程 | JSON 文本 → PKCS7 → AES-CBC → Base64；响应同理，需要读取响应中的 `suffix` 解密 |
| 成功响应 | `data` 解密后包含 `token`、`vip_level`、`is_vip` 等信息 |

## 4. 分类与专题
- 分类数据位于 `https://bbmjs.pki.net.cn/data/category/base-2.js`，返回结构化 JSON，字段示例：`section`、`name`、`jump_name`、`channel`、`topic_id`。
- 普通频道列表：`https://bbmjs.pki.net.cn/data/list/base-{channel}-{jump_name}-{page}.js`。
- 专题（`channel == "topic"`）需额外请求 `https://bbmjs.pki.net.cn/data/topic/details-{topic_id}-0.js` 获取附加信息（标题、描述、售价等）。

## 5. `maomi_spider.py`
- 面向命令行，可在调试/脚本环境直接调用 `MaomiClient`：
  ```bash
  python maomi_spider.py \
    --username <你的账号> \
    --password <你的密码> \
    --category mmtj \
    --pages 3 \
    --output result.json
  ```
- 支持：
  - `--list-categories`：打印全部分类，含频道信息与是否受支持。
  - `--pages 1-5`：分页抓取前 N 页，自动根据接口 `last_page` 终止。
  - 输出 JSON 包含 `account`（VIP 等级）、`category`（频道、抓取页数、专题元信息）与 `videos` 数组。
- `videos` 字段示例：
  ```json
  {
    "id": 41021059,
    "title": "示例标题",
    "tags": "猫咪推荐,每日更新",
    "duration_seconds": 863,
    "duration_hms": "00:14:23",
    "video_mp4": "https://www.mmxzxl1.com/...mp4",
    "video_m3u8": "https://www.mmxzxl1.com/...m3u8",
    "thumb_url": "https://jpg.tlxxw.cc/...jpg.txt?size=500x281",
    "detail_url": "https://www.a3k3c.com/play/41021059.html"
  }
  ```

## 6. `web_app.py`
- Flask 路由：
  | 路径 | 方法 | 说明 |
  | --- | --- | --- |
  | `/` | GET | 控制台 UI（账号输入、分类下拉、页数、状态日志、视频卡片、JSON 弹窗） |
  | `/api/categories` | POST | 使用输入的账号密码实时登录并返回分类列表 |
  | `/api/scrape` | POST | 登录→匹配分类→抓取前 N 页→返回视频信息；响应中移除用户名，仅包含 VIP 等级 |
- UI 调整要点：
  - 删除图片、下载相关逻辑，仅展示文字信息和 JSON。 
  - 点击"详情(JSON)"弹出遮罩层，显示 `JSON.stringify(video, null, 2)`，可复制。
  - "原站页面"按钮便于跳转至官网播放页核对数据。
  - 底部日志区记录每次 API 调用状态，便于分析。

## 7. 安全约束
- 代码不会持久化账号，所有凭据仅在当前请求中使用。
- 返回体不再包含 `username` 等敏感字段，便于开源分享。
- 项目不包含下载/存储视频的实现，保留在协议层学习的范畴。

## 8. 可拓展方向
- 增加 `requests.Session` + Cookie/TOKEN 缓存，减少重复登录成本。
- 提供代理、超时、失败重试等参数，适配更复杂的网络环境。
- Web 控制台可对接本地数据库或搜索功能，用于快速检索抓取记录。
- 若需要导出数据，可在前端新增"导出 JSON"按钮，而不是直接下载视频。
