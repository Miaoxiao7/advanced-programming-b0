# 检查记录（B0）

- 版本：`b0/summary-service` 分支首个提交，2026-11-24；演示版补充 2026-11-26
- 参考环境：Windows，Python 3.9.21（venv），ruff 0.6.9，coverage 7.6.1，无 GPU
- 说明：表中的"预期"均为手算或按约定推导，不复制程序输出；"实际"为当次真实运行的
  原始结果。

## 一 静态检查与格式

| 编号 | 命令 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C1 | `ruff check .` | 无告警 | `All checks passed!` | 一致 |
| C2 | `ruff format --check .` | 无文件需要重新格式化 | `7 files already formatted` | 一致 |

## 二 自动测试与覆盖率

| 编号 | 命令 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C3 | `python -m unittest discover -s tests` | 全部用例通过 | `Ran 47 tests` / `OK`，连续 3 次结果一致 | 一致 |
| C4 | `python -m coverage run --source=b0_stats -m unittest discover -s tests` + `coverage report -m` | 覆盖率接近满值，仅启动入口未覆盖 | `stats.py 100%`、`service.py 100%`、`app.py 99%`（未覆盖 `app.py:105`）、`TOTAL 99%` | 一致，缺口为 `if __name__ == "__main__"` 下的调用行 |

## 三 正常条件（真实 HTTP 调用）

| 编号 | 输入 | 预期（手算依据） | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C5 | `GET /health` | `200`，含 `status=ok` | `200`，`Content-Length: 47`，正文 `{"status": "ok", "service": "b0-stats-summary"}` | 一致 |
| C6 | `POST /api/summary`，`{"values": [1,2,3,4]}` | count=4；mean=10/4=**2.5**；median=(2+3)/2=**2.5**；离差平方和 2.25+0.25+0.25+2.25=5，样本方差 5/3，std=**1.290994**；q1=1+0.75=**1.75**，q3=3+0.25=**3.25**，IQR=**1.5**；栅栏 −0.5/5.5，无异常值 | `200`，`{"count": 4, "mean": 2.5, "median": 2.5, "std_sample": 1.290994, "min": 1.0, "max": 4.0, "q1": 1.75, "q3": 3.25, "iqr": 1.5, "outliers": [], "outlier_count": 0}` | 一致 |
| C7 | `POST /api/summary`，`{"values": [1,2,3,4,5,100]}` | count=6；mean=115/6=**19.166667**；median=(3+4)/2=**3.5**；离差平方和约 7850.83，样本方差 1570.17，std≈**39.625329**；q1=**2.25**，q3=**4.75**，IQR=2.5，上栅栏 4.75+3.75=8.5 → 100 越界 | `200`，`{"count": 6, "mean": 19.166667, "median": 3.5, "std_sample": 39.625329, "min": 1.0, "max": 100.0, "q1": 2.25, "q3": 4.75, "iqr": 2.5, "outliers": [100.0], "outlier_count": 1}` | 一致 |

## 四 异常条件

| 编号 | 输入 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C8 | `{"values": []}` | `400`，`empty_input`（空数组无法给出均值） | `400`，`{"error": "empty_input", "message": "values must not be empty"}` | 一致 |
| C9 | `{"values": ["a"]}` | `400`，`not_a_number` | `400`，`{"error": "not_a_number", "message": "values[0] is not a number"}` | 一致 |
| C10 | `GET /nope` | `404`，`not_found` | `404` | 一致 |
| C11 | 请求体 `{` | `400`，`invalid_json` | 单元测试通过（`test_broken_json`、`test_broken_json_over_http`） | 一致 |
| C12 | `Content-Length: abc` | `400`，`invalid_length`（不读取正文） | 单元测试通过（`BrokenHeaderTest`） | 一致 |
| C13 | `Content-Length: 999` 且上限设为 16 字节 | `413`，`body_too_large`，且发生在读取正文之前 | 单元测试通过（`PayloadLimitTest`） | 一致 |
| C14 | `values` 只有 1 个数值 | `400`，`too_few_samples` | 单元测试通过（`test_single_sample`） | 一致 |
| C15 | `values` 含 `NaN` / `Infinity` | `400`，`not_a_number` | 单元测试通过（`test_not_finite_item`） | 一致 |

## 五 演示页（2026-11-26 补充）

| 编号 | 输入 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C16 | `GET /` | `200`，`text/html`，正文含页面标题 | `200`，`text/html; charset=utf-8`，12304 字节，含「统计摘要演示」 | 一致 |
| C17 | `GET /demo?from=readme` | 查询串被忽略，返回与 C16 同一页 | `200`，12304 字节，与 C16 相同 | 一致 |
| C18 | `POST /`，正文 `{}` | 静态路由不接管 POST，仍由 JSON 服务判定为未知路径 | `404`，`{"error": "not_found", "message": "unknown route: /"}` | 一致 |
| C19 | 演示页点「含一个异常值」后提交 | 页面数值应与 C7 逐项一致 | 页面显示 count=6、mean=19.166667、median=3.5、std=39.625329、q1=2.25、q3=4.75、iqr=2.5，异常值标签 `100` | 一致（本机 Edge 无头渲染截图核对） |

## 六 扩展指标（2026-11-26 补充）

新增字段的手算依据与实测输出。三组输入的均值分别为 2.5、19.166667、0。

| 编号 | 输入 | 预期（手算） | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| C20 | `[1, 2, 3, 4]` | 离差平方和 5；样本方差 5/3=**1.666667**；总体方差 5/4=**1.25**；平方和 30，rms=√7.5=**2.738613**；绝对峰值 **4**；峰峰值 4−1=**3**；全为正，过零率 **0** | `{"variance_sample": 1.666667, "variance_population": 1.25, "rms": 2.738613, "peak": 4.0, "peak_to_peak": 3.0, "zero_crossing_rate": 0.0}` | 一致 |
| C21 | `[1, 2, 3, 4, 5, 100]` | 离差平方和约 7850.83；样本方差 7850.83/5=**1570.166667**；总体方差 /6=**1308.472222**；平方和 10055，rms=√(10055/6)=**40.936943**；峰值 **100**；峰峰值 **99**；过零率 **0** | `{"variance_sample": 1570.166667, "variance_population": 1308.472222, "rms": 40.936943, "peak": 100.0, "peak_to_peak": 99.0, "zero_crossing_rate": 0.0}` | 一致 |
| C22 | `[1, -1, 2, -2, 3, -3]` | 均值 0，平方和 28；样本方差 28/5=**5.6**；总体方差 28/6=**4.666667**；rms=√(28/6)=**2.160247**；峰值 **3**；峰峰值 3−(−3)=**6**；符号序列 +−+−+−，5 次变化 /5=**1.0** | `{"variance_sample": 5.6, "variance_population": 4.666667, "rms": 2.160247, "peak": 3.0, "peak_to_peak": 6.0, "zero_crossing_rate": 1.0}` | 一致 |
| C23 | 演示页依次点「正常四样本」「含一个异常值」「正负交替」 | 三次页面数值应与 C20–C22 逐项一致，折线图红点数量分别为 0、0、5 | 三组数值与上表一致；「正负交替」折线在 5 个过零点显示红点并叠加零线，最高点标蓝点 | 一致（Edge 无头渲染截图核对） |

过零率的口径核对：`[1, 2, 3, 4]`（全正）为 0，`[1, 2, -3, 4]` 为 2/3=0.666667（符号 ++−+），
`[0, 1]` 为 0（零计为非负），`[-1, 1]` 为 1.0，均已写入单元测试。

演示页的 C16–C19 不新增接口：页面调用的仍是 C5–C7 的 `GET /health` 与 `POST /api/summary`，
故 C5–C15 的原有结论不受影响。

## 七 未覆盖与待办

1. `app.py:105`（`if __name__ == "__main__"` 内的 `main()` 调用）未计入覆盖率，属入口行；
   `main()` 本身已由 `MainTest` 覆盖，包括就绪输出与 `server_close()` 的调用。
2. 1 MB 的真实体积上限只用 16 字节的小上限等价复现，未发送 1 MB 请求体（避免拖慢用例）。
3. 未做并发与长时间运行检查，见 `docs/limits.md` 第 4 条。
