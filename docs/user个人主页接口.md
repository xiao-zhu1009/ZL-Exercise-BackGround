# 用户个人主页接口说明

路由定义在 `api/user.py`，经 `main.py` 挂载后**统一前缀**为 `/api`，本模块路由前缀为 `/user`，即完整路径形如 `/api/user/...`。

**鉴权**：以下接口均需在请求头携带登录后获得的 JWT：

`Authorization: Bearer <token>`

未携带或 Token 无效时，由鉴权依赖直接返回错误，不会进入业务处理。

---

## 统一响应格式

与全项目一致（`utils/response.py`）：

| 场景 | HTTP 状态码 | Body 结构 |
|------|-------------|-----------|
| 成功 | 200 | `{ "code": 200, "message": "提示文案", "data": ... }` |
| 业务失败 | 与 `code` 一致（如 400/401/404） | `{ "code": <数字>, "message": "错误说明", "data": null }` |

除「上传头像」外，请求体一般为 **JSON**，`Content-Type: application/json`。

---

## 接口索引

| 序号 | 说明 | 方法与路径 |
|:----:|------|------------|
| 1 | 获取个人信息 | `GET` `/api/user/profile` |
| 2 | 修改个人信息 | `PUT` `/api/user/profile` |
| 3 | 上传头像 | `POST` `/api/user/avatar` |
| 4 | 获取身体指标 | `GET` `/api/user/body-stats` |
| 5 | 修改身体指标 | `PUT` `/api/user/body-stats` |
| 6 | 修改密码 | `PUT` `/api/user/password` |

---

## 1. 获取个人信息

| 项目 | 内容 |
|------|------|
| 路径 | `GET /api/user/profile` |
| 作用 | 读取当前登录用户在个人主页展示的基础资料（昵称、手机、签名、头像等） |

**请求**：无 Query、无 Body（身份由 `Authorization` 解析）。

**成功时 `data`**

| 字段 | 说明 |
|------|------|
| `username` | 用户名 |
| `nickname` | 昵称 |
| `phone` | 手机号 |
| `signature` | 个性签名 |
| `avatar` | 头像 URL，可能为 `null` 或空 |

**说明**：若 Token 有效但用户记录不存在，返回 **404** 等业务错误信封。

---

## 2. 修改个人信息

| 项目 | 内容 |
|------|------|
| 路径 | `PUT /api/user/profile` |
| 作用 | 部分更新个人资料；仅提交需要修改的字段即可（Pydantic `exclude_unset`） |

**请求体字段**（均为可选，按需提供）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `nickname` | string | 否 | 昵称 |
| `phone` | string | 否 | 手机号 |
| `signature` | string | 否 | 个性签名 |
| `avatar` | string | 否 | 头像地址；传 **`""`（空字符串）** 表示恢复默认头像 |

**成功时 `data`**：`null`，`message` 一般为「保存成功」。

---

## 3. 上传头像

| 项目 | 内容 |
|------|------|
| 路径 | `POST /api/user/avatar` |
| 作用 | 上传图片文件，保存到 `static/avatars`，将可访问 URL 写回 `users.avatar` 并返回 |

**请求**

| 项目 | 说明 |
|------|------|
| `Content-Type` | `multipart/form-data` |
| 表单字段 | `file`：文件（必填） |

**允许类型**：`image/jpeg`、`image/png`、`image/webp`、`image/gif`；扩展名与类型需合理（服务端会对未知扩展名按类型默认 `.jpg` / `.png`）。

**大小限制**：不超过 **2MB**。

**成功时 `data`**

| 字段 | 说明 |
|------|------|
| `avatar` | 完整可访问 URL（形如 `{服务根}/api/static/avatars/{文件名}`，根地址来自请求的 `base_url`） |

**常见业务错误**：非允许图片类型（400）、用户不存在（404）、超过 2MB（400）。

---

## 4. 获取身体指标

| 项目 | 内容 |
|------|------|
| 路径 | `GET /api/user/body-stats` |
| 作用 | 查询当前用户身体指标；若尚未录入过记录，成功时 `data` 为 `null` |

**请求**：无 Query、无 Body。

**成功时 `data`**

| 情况 | 说明 |
|------|------|
| 无记录 | `data` 为 `null` |
| 有记录 | 见下表 |

**有记录时 `data` 字段**

| 字段 | 说明 |
|------|------|
| `height` | 身高 |
| `weight` | 体重 |
| `bmi` | BMI，保留 1 位小数；无则 `null` |
| `body_fat` | 体脂率等（与模型字段一致） |
| `waist` | 腰围 |
| `hip` | 臀围 |
| `whr` | 腰臀比，保留 2 位小数；无则 `null` |

---

## 5. 修改身体指标

| 项目 | 内容 |
|------|------|
| 路径 | `PUT /api/user/body-stats` |
| 作用 | 新增或更新身体指标；服务端会根据身高、体重、腰围、臀围等**自动计算 BMI、WHR**（与 CRUD 逻辑一致） |

**请求体字段**（均为可选）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `height` | number | 否 | 身高 |
| `weight` | number | 否 | 体重 |
| `body_fat` | number | 否 | 体脂率等 |
| `waist` | number | 否 | 腰围 |
| `hip` | number | 否 | 臀围 |

**成功时 `data`**

| 字段 | 说明 |
|------|------|
| `bmi` | 计算后的 BMI，1 位小数；无则 `null` |
| `whr` | 计算后的腰臀比，2 位小数；无则 `null` |

---

## 6. 修改密码

| 项目 | 内容 |
|------|------|
| 路径 | `PUT /api/user/password` |
| 作用 | 校验旧密码后更新为新密码（当前实现为明文比对存储字段，与现有 `api/user.py` 一致） |

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `old_password` | string | 是 | 当前密码 |
| `new_password` | string | 是 | 新密码 |

**成功时 `data`**：`null`，`message` 一般为「密码修改成功」。

**常见业务错误**：新旧密码相同（400）、旧密码错误（400）。

---

## 补充说明

1. **静态资源访问**：头像等资源通过 `GET /api/static/...` 访问（由 `main.py` 挂载 `StaticFiles`）。
2. **头像两种改法**：可在「修改个人信息」里传 `avatar` 字符串或 `""`；也可单独调用「上传头像」由服务端生成 URL。
3. **角色与权限**：本文件仅描述 **`/api/user/*` 个人主页能力**；超管、教练等其它模块路由见各自 `api` 文件。
