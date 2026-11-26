# B0 个人实验：实验数据统计摘要服务

本仓库是「研究生高级程序设计（实践）」课程第 1 周个人实验 B0 的交付物。
课程材料来源：课程 Git 仓库 README v0.5（2026-11-23）与《项目组织与提交要求》v0.5。
B0 不套用团队项目的代码规模、六单元比较矩阵或 18 次训练要求，只要求本人走通
「需求 → 设计 → 实现 → 检查 → 交付」的完整过程。

## 一 目的与范围

**目标使用者**：本人（数据整理者）与接收者（同伴或教师）。使用者手上有一组测量值，
需要在不写代码的情况下得到描述统计与异常值提示，并能核对每一个数值的来源。

**解决的问题**：把一组数值转换为可直接引用的统计摘要，同时明确拒绝无法给出有意义
结论的输入（空数组、非数值、样本数不足、超限），避免"用错误的数算出漂亮的结果"。

**本次交付包括**：一个只监听本机回环地址的 HTTP 服务，两个 JSON 接口，一个只读静态演示页，
一套可重复执行的检查（单元测试 + 覆盖率 + 静态检查），以及 CI 流水线。

**本次不包括**：数据持久化、账号与鉴权、批量文件导入、并发任务调度、产品化前端。演示页只是
展示层，不含校验逻辑，也不改变下述接口契约。

## 二 接口契约

服务默认监听 `127.0.0.1:8000`，请求与响应均为 JSON（`application/json; charset=utf-8`）。

| 接口 | 调用方式 | 输入 | 成功返回 |
| --- | --- | --- | --- |
| 健康检查 | `GET /health` | 无输入 | `200` + `{"status": "ok", "service": "b0-stats-summary"}` |
| 统计摘要 | `POST /api/summary` | `{"values": [数值, ...]}`，2–10000 个有限数值 | `200` + 摘要对象（字段见下表） |

另有两个只读静态路由 `GET /` 与 `GET /demo`，返回演示页 HTML（`text/html; charset=utf-8`），
不带 `values` 参数、不产生 JSON 响应，因此不进入下表的错误码口径；对这两个路径使用 `POST`
仍按普通请求处理，返回 `404 not_found`。

摘要对象字段：`count`、`mean`、`median`、`std_sample`（样本标准差）、`min`、`max`、
`q1`、`q3`、`iqr`、`outliers`（超出 1.5×IQR 栅栏的值）、`outlier_count`。
除 `count` 与离散值外，数值统一保留 6 位小数。

| 状态码 | `error` 代码 | 触发条件 |
| --- | --- | --- |
| 400 | `missing_body` | 请求体为空 |
| 400 | `invalid_json` | 请求体不是合法 JSON，或不是 UTF-8 |
| 400 | `missing_values` | JSON 不是对象，或缺少 `values` 字段 |
| 400 | `invalid_type` | `values` 不是数组 |
| 400 | `empty_input` | `values` 为空数组 |
| 400 | `not_a_number` | 元素不是数值、是布尔值，或为 `NaN` / `Infinity` |
| 400 | `too_few_samples` | 数值少于 2 个（无法计算样本标准差） |
| 400 | `too_many_samples` | 数值超过 10000 个 |
| 400 | `invalid_length` | `Content-Length` 不是整数 |
| 404 | `not_found` | 路径不存在 |
| 405 | `method_not_allowed` | 方法与路径不匹配 |
| 413 | `body_too_large` | 请求体超过 1 MB（在读取正文前拒绝） |

## 三 结构与调用关系

请求进入 `SummaryHandler`（`b0_stats/app.py`）后，只做与 HTTP 相关的事：解析
`Content-Length`、限制体积、读取正文、写出响应。全部判定逻辑交给
`service.handle`（`b0_stats/service.py`），数值计算再下沉到 `stats`（`b0_stats/stats.py`）。
因此不含套接字的契约测试可以覆盖绝大多数分支，socket 测试只验证传输层。

| 名称 | 位置 | 职责 | 关键属性或操作 |
| --- | --- | --- | --- |
| `SummaryHandler` | `b0_stats/app.py` | 把 HTTP 请求映射为服务调用 | `max_body_bytes` 限制正文体积；`_respond` 组织读取与回写 |
| `make_server` | `b0_stats/app.py` | 创建并返回服务器实例 | 传入端口 `0` 时由系统分配空闲端口，供测试使用 |
| `main` | `b0_stats/app.py` | 解析参数、启动服务、打印就绪行 | `--host` / `--port`；输出 `ready: listening on ...` |
| `handle` | `b0_stats/service.py` | 路由与方法校验、JSON 解析、错误码映射 | 返回 `(status, payload)` 二元组，不依赖 socket |
| `summarise` | `b0_stats/stats.py` | 计算摘要与异常值 | 先校验再排序计算，返回可直接序列化的字典 |
| `coerce_values` | `b0_stats/stats.py` | 输入校验与类型归一 | 拒绝布尔值、非有限数、越界样本数 |
| `percentile` | `b0_stats/stats.py` | 线性插值分位数 | 与常见数值库默认的线性插值口径一致 |
| `StatsError` | `b0_stats/stats.py` | 携带稳定错误码的领域异常 | `code` 决定返回给客户端的 `error` 字段 |

## 四 运行

运行时只用 Python 3.9 标准库，无需安装第三方包；第三方工具仅用于检查。

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # 仅静态检查与覆盖率需要

python -m b0_stats.app --port 8000
```

**就绪判据**：终端出现 `ready: listening on http://127.0.0.1:8000`，且
`curl http://127.0.0.1:8000/health` 返回 `200` 与 `{"status": "ok", ...}`。

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/api/summary \
  -H "Content-Type: application/json" -d '{"values": [1, 2, 3, 4]}'
curl -s -X POST http://127.0.0.1:8000/api/summary \
  -H "Content-Type: application/json" -d '{"values": [1, 2, 3, 4, 5, 100]}'
curl -s -X POST http://127.0.0.1:8000/api/summary \
  -H "Content-Type: application/json" -d '{"values": []}'
```

预期结果见 `docs/check-log.md`，其中每组输入都附有手算依据。

### 演示入口

启动后浏览器打开 `http://127.0.0.1:8000/`（等价 `http://127.0.0.1:8000/demo`）。终端同时会
打印 `demo: http://127.0.0.1:8000/`，可直接复制该行地址。

1. 页面打开即用默认样本 `1, 2, 3, 4, 5, 100` 自动计算一次，用于确认服务在线；
2. 点「正常四样本」「含一个异常值」「只有 1 个样本」「空数组」「非数值」任一预设，再点
   「计算摘要」（或按 Ctrl + Enter），结果区立即刷新；
3. 展开「原始响应 JSON」逐字核对数值；点「清空结果」回到初始态。

演示页与命令行调用的是同一个 `POST /api/summary`：输入框只做分隔符拆解（逗号、空格、换行，
或直接粘贴 JSON 数组），是否合法、能否计算全部由服务端判定，因此页面上出现的 `400`
错误码与 curl 结果完全一致。

## 五 检查与 CI

```bash
ruff check .                 # 静态检查，规则见 pyproject.toml（对应课程 A1–A4）
ruff format --check .        # 格式检查（课程 A2，行宽 88、双引号、4 空格）
python -m coverage run --source=b0_stats -m unittest discover -s tests
python -m coverage report -m
```

当前结果：41 个用例全部通过，静态检查与格式检查无告警，`b0_stats` 覆盖率 99%
（唯一未覆盖行为 `app.py` 第 105 行 `if __name__ == "__main__"` 下的调用）。

CI 位于 `.github/workflows/check.yml`，在每次推送 `main` 与每个 PR 上执行上述四步；
任一步失败即返回非零退出码，不设 `continue-on-error`，也不跳过测试。

## 六 限制

当前限制、未覆盖的范围与对应处理方式见 `docs/limits.md`。

## 七 目录

```
b0_stats/            服务实现（app / service / stats）与只读演示页 demo.html
tests/               单元测试与端到端测试
docs/check-log.md    检查记录（输入、预期、实际、结论）
docs/limits.md       限制与未完成事项
pyproject.toml       ruff 规则与格式配置
requirements-dev.txt 开发工具版本（ruff 0.6.9、coverage 7.6.1）
.github/workflows/   CI 流水线
```
