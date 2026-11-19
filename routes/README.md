# Throne 路由导出（SmartRoute × out-ai）

从本机 Throne（`D:/program/Throne/config/throne.db`，只读）导出的两条路由，
发布于 <https://proxy-route.shkits.com>（GitHub Pages，main 分支 `routes/` 变更自动发布）。导出时间：2026-11-19。

| Throne 路由 | 语义 | 兜底（final/MATCH） |
|---|---|---|
| **SmartRoute(CN whitelist: ai-bb)** | 大陆/内网/私有域名直连，AI 及特殊 US 域名走 out-ai，**其余全部走代理**（白名单模式） | `proxy` |
| **SmartRoute(proxy list: ai-bb)** | 同上直连规则，外加 GFW/Telegram/国外域名走主代理，**其余全部直连**（代理名单模式） | `direct` |

两条路由的差异仅三处：proxy list 版多 `geosite-category-dev-cn` 直连、多「Proxy域名」一组规则、兜底不同。

站点首页（各工具订阅 URL 速查）见 [index.html](index.html)。

## 出站占位符 `out-ai`：如何指定实际接入点

导出**不含任何节点凭据**。`out-ai` 是出站引用名，各工具在自己的配置里把它绑定到实际节点——绑定一次，规则文件不用改：

| 工具 | 绑定方法 |
|---|---|
| sing-box / Throne | 在 `outbounds` 里定义任意类型的出站并 `"tag": "out-ai"`（具体节点或 selector/url-test 组均可） |
| mihomo / Clash Verge | 建一个名为 `out-ai` 的策略组（`type: select`/`url-test`，含目标节点），或把 YAML 里 `out-ai` 全局替换为已有组名 |
| v2rayN 路由规则 | outboundTag 直接填**节点别名或策略组名**（7.x 新版支持分流到指定节点）；或走「完整配置模板」方式在模板 outbounds 里定义 |
| Throne 订阅导入 | Throne 分享格式按**节点名**解析出站：本机需存在名为 `vr-us-bb.shkits.com(AnyTLS)` 的节点；不存在则该组回退 proxy 并给出警告 |

其余占位符：`direct`/`DIRECT` = 直连（Throne -2）；`proxy`/`PROXY` = 主出站（Throne -1，当前选中节点）。

## 文件清单与订阅 URL

```
sing-box/
  smartroute-cn-whitelist-out-ai.json   # route 片段：rules(已合并) + rule_set(远程 URL) + final
  smartroute-proxy-list-out-ai.json
  rule-set-src/                         # 自定义规则 → sing-box 源格式 rule-set，format:"source" 直接订阅
    direct-private.json / out-ai-keywords.json / out-ai-domains.json
mihomo/
  smartroute-cn-whitelist-out-ai.yaml   # rules + rule-providers 片段（providers 已指向本站）
  smartroute-proxy-list-out-ai.yaml
  providers/                            # mihomo rule-provider（classical），本站自托管
    direct-private.yaml / out-ai-keywords.yaml / out-ai-domains.yaml
v2rayN/
  smartroute-cn-whitelist-out-ai.rules.json    # v2rayN 自定义路由规则数组（已合并，3/4 条）
  smartroute-proxy-list-out-ai.rules.json      # 路由设置 → 导入规则 → 从订阅URL导入
  singbox-custom-ruleset.json                  # v2rayN「自定义 sing-box rule set」映射，14 个 tag 与 Throne 同源
throne/
  smartroute-cn-whitelist-out-ai.txt    # Throne 路由订阅（throne://route/ deeplink，一行）
  smartroute-proxy-list-out-ai.txt
  add-both-remote.txt                   # throne://remoteroute/ 一次性订阅两条（导入端 b64 解码需宽松处理，失败则分别添加上面两个 URL）
lists/                                  # 纯文本（每行一条），供 AdGuard/dnsmasq/SwitchyOmega 等
  direct-private-suffix.txt / direct-private-regex.txt / out-ai-keywords.txt / out-ai-domains.txt
```

订阅 URL 前缀统一为 `https://proxy-route.shkits.com/`，如 `https://proxy-route.shkits.com/mihomo/providers/direct-private.yaml`。

公共 rule-set 使用的 URL 与 Throne 内置注册表一致（MetaCubeX meta-rules-dat `sing` 分支；
`geoip-openai` 为 Chocolate4U/Iran-sing-box-rules——mihomo 无此集合，改用 `geoip/ai.yaml` 即 ipinfo AI 类别，文件内有注释）。

## raw.githubusercontent.com 下载可达性（三层保障）

1. **sing-box / v2rayN（sing-box 内核）**：`rule_set` 均带 `download_detour: "proxy"`，规则集经代理出站下载——核心机制，天然解决。
2. **mihomo**：指向 raw.githubusercontent.com 的 rule-provider 已附 `proxy: PROXY`（下载/更新走指定代理组；把 `PROXY` 换成你的组名，不需要可删）。注意 mihomo 有 urltest 组作 provider 代理的已知 bug（MetaCubeX/mihomo#3163），建议用固定 select 组。
3. **无代理/兜底**：URL 换 jsdelivr 镜像（直连可达），格式对照：
   - `https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/cn.srs`
     → `https://cdn.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@sing/geo/geoip/cn.srs`
   - `https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-openai.srs`
     → `https://cdn.jsdelivr.net/gh/Chocolate4U/Iran-sing-box-rules@rule-set/geoip-openai.srs`
   另外 **Throne 自身**拉取 githubusercontent 的订阅/规则时会自动改写为 jsdelivr（`get_jsdelivr_link`）；本站 `proxy-route.shkits.com` 非 githubusercontent，Throne 直接拉取。

## 规则合并说明（相对 Throne 逐条形式的优化）

Throne 里每个"规则组"是一条规则；sing-box/v2rayN 导出把**相邻且同出站**的规则段合并，匹配语义与逐条形式严格等价（只做相邻合并，段间先后顺序保持不变）：

| 格式 | 合并方式 | 结果 |
|---|---|---|
| sing-box | 单条规则内不同字段是 AND 语义，用 `logical` + `mode:"or"` 包裹成子规则 OR | 8/9 条 → 3/4 条（含 hijack-dns） |
| v2rayN | Xray 规则内 `domain[]`/`ip[]` 条目本身是 OR，直接拼接数组（v2rayN 转 sing-box 内核时会自动再拆分） | 15/19 条 → 3/4 条 |
| mihomo | **不合并**：每行规则 = 单个匹配动作；自定义列表已经用 rule-provider 合并。把上游 geosite 集也合并成自托管文件会失去上游自动更新，不建议 | 保持逐行 |
| Throne 订阅 | **不合并**：保持 Throne 分享格式（throne-route-profile v1）逐条形式，导入后与手工配置无异 | 8/9 条 |

合并后的等价性经脚本校验（各段匹配器并集与 throne.db 逐条形式一致）。

## v2rayN 接入（三种方式）

1. **完整配置模板（推荐，与本机现状一致）**：把 `sing-box/*.json` 里的 `route.rules` 按需并入模板（模板已有更细的 DNS/进程/BT 规则，注意先后顺序），`out-ai` ↔ 模板中 `out-proxy-ai` 二选一改名；`rule_set` 引用可继续用本地 `ext-srss`，或换成导出文件里的远程 URL。
2. **路由规则 + 自定义 ruleset（纯 GUI，支持 URL 订阅）**：
   - 设置 → 路由设置 → 「自定义 sing-box rule set」填入 `v2rayN/singbox-custom-ruleset.json` 内容（14 个 tag 与 Throne 完全同源，解析优先级最高）；
   - 路由规则 → 导入规则 → 从文件/剪贴板/订阅 URL 导入 `*.rules.json`；
   - DNS 劫持由 v2rayN 内置 DNS 模块处理，无需导入；
   - `geoip:openai` 一条仅 sing-box 内核可解析（Xray 的 geoip.dat 无此类别），备注中已标注。
3. **自定义配置整体导入**：把 sing-box 片段补全 inbounds/outbounds 后做成完整 config，v2rayN 以「自定义配置」方式加载。

## 发布（CI）

`.github/workflows/deploy-routes-pages.yml`：main 分支 `routes/**`（或工作流文件本身）变更时，
把 `routes/` 目录作为静态站点发布到 GitHub Pages。首次使用需：

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**；
2. DNS 添加 CNAME 记录：`proxy-route.shkits.com` → `<github账号>.github.io`；
3. 仓库 Settings → Pages → Custom domain 填 `proxy-route.shkits.com`（`routes/CNAME` 文件已就位），勾选 Enforce HTTPS。

## 复现 / 更新

```
python -I scripts/export_throne_routes.py          # 默认输出到 routes/
python -I scripts/export_throne_routes.py <目录>    # 或指定输出目录
```

脚本只读打开 `throne.db`，重新导出只清理生成子目录（`sing-box/mihomo/v2rayN/lists/throne`），
不碰 `index.md`/`README.md`/`CNAME`/`.nojekyll`。导出内容已与数据库逐字段比对一致
（规则顺序、41+3 私有域名、4 关键字、5 特殊域名、14 个 rule-set、final 出站；合并形式与 Throne deeplink 均经往返校验）。
