# Throne 路由导出（SmartRoute × out-ai）

从本机 Throne（`D:/program/Throne/config/throne.db`，只读）导出的两条路由，
发布于 <https://proxy-route.shkits.com>（GitHub Pages，main 分支 `routes/` 变更自动发布）。导出时间：2026-11-19。

| Throne 路由 | 语义 | 兜底（final/MATCH） |
|---|---|---|
| **SmartRoute(CN whitelist: ai-bb)** | 大陆/内网/私有域名直连，AI、Google 及特殊 US 域名走 out-ai，**其余全部走代理**（白名单模式） | `proxy` |
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
| Throne 订阅 / Raw 导入 | 按**节点名**解析出站，本机需有名为 `vr-us-bb.shkits.com(AnyTLS)` 的节点。缺少同名节点时回退到 `proxy` 并提示 |

其余占位符：`direct`/`DIRECT` = 直连（Throne -2）；`proxy`/`PROXY` = 主出站（Throne -1，当前选中节点）。

## 文件清单与订阅 URL

```
sing-box/
  smartroute-cn-whitelist-out-ai.json   # 顶层 http_clients + route.rules / rule_set / final
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
throne/
  smartroute-cn-whitelist-out-ai.txt    # 结构化路由订阅（throne://route/ deeplink，一行）
  smartroute-proxy-list-out-ai.txt
  smartroute-*.raw.txt                 # Throne 1.4.2+ Raw 路由，手动导入
  add-both-remote.txt                   # throne://remoteroute/ 一次性订阅两条（导入端 b64 解码需宽松处理，失败则分别添加上面两个 URL）
lists/                                  # 纯文本（每行一条），供 AdGuard/dnsmasq/SwitchyOmega 等
  direct-private-suffix.txt / direct-private-regex.txt / out-ai-keywords.txt / out-ai-domains.txt
```

订阅 URL 前缀统一为 `https://proxy-route.shkits.com/`，如 `https://proxy-route.shkits.com/mihomo/providers/direct-private.yaml`。

公共规则集来自 MetaCubeX `meta-rules-dat`。`geoip-openai` 的 sing-box SRS 来自 Chocolate4U，mihomo 对应规则沿用 MetaCubeX 的 `geoip/ai.mrs`，数据范围是 ipinfo 的 AI 类别。

## Google 规则集与优先级

两套策略的 `out-ai` 都引用 `geosite-google` 和 `geoip-google`。Google 域名集覆盖搜索、Gmail、Gemini、YouTube 等服务。
sing-box 和 Throne 使用 MetaCubeX 的 SRS，v2rayN 的 sing-box 内核可加载同一份 SRS，mihomo 使用同项目的 `domain` MRS provider。v2rayN 的 Xray 内核使用本地 `geosite.dat` 中的 `geosite:google`。
[MetaCubeX SRS](https://github.com/MetaCubeX/meta-rules-dat/blob/sing/geo/geosite/google.srs) · [MetaCubeX MRS](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geosite/google.mrs)

直连规则的优先级高于 `out-ai`。当前上游同时把 `google.cn`、`gstatic.cn` 等收入 `geosite-cn` 和 `geosite-google`，这些域名先命中直连。常规 Google 域名如 `www.google.com`、`www.youtube.com` 命中 `out-ai`。

## 规则集下载与缓存

- **sing-box 1.14+** 的 `rule_set` 通过 `http_client` 引用顶层 `http_clients` 中的 `smartroute-rulesets`，由 `proxy` 出站下载。合并片段时要同时合并顶层 `http_clients` 和 `route`。完整配置可以用 `experimental.cache_file.enabled` 保留下载缓存。 [sing-box 规则集](https://sing-box.sagernet.org/configuration/rule-set/)
- **mihomo** 的公网域名和 IP provider 使用 MRS，包含正则和关键字的自定义 provider 使用 classical YAML。公网集合通过 `proxy: PROXY` 下载。 [mihomo Rule Providers](https://wiki.metacubex.one/en/config/rule-providers/)
- **Throne 1.4.2** 的远程订阅只接受结构化路由，SRS 下载客户端由 Throne 生成，当前仍使用内核的隐式默认 HTTP client。需要显式 HTTP client 时，复制 `*.raw.txt` 的链接并手动导入，在 Raw Route 编辑器中查看。Raw 版的 SRS 随内核定期更新，路由策略更新通过重新导入应用。 [Throne 远程订阅源码](https://github.com/throneproj/Throne/blob/1.4.2/src/configs/sub/RouteUpdater.cpp) · [Throne 规则集生成源码](https://github.com/throneproj/Throne/blob/1.4.2/src/configs/generate.cpp)

## 规则合并说明（相对 Throne 逐条形式的优化）

sing-box 和 v2rayN 导出会合并**相邻且同出站**的规则，保留出站段的先后顺序。

| 格式 | 合并方式 | 结果 |
|---|---|---|
| sing-box / Throne Raw | `rule_set` 数组中的各集合按 OR 匹配。外层 `logical` + `mode:"or"` 允许自定义匹配器与规则集各自命中 | 4/5 条（含 sniff 和 hijack-dns） |
| v2rayN | 订阅条目保留 `domain[]` 和 `ip[]`。v2rayN 为 sing-box 和 Xray 生成配置时会将两者拆成独立规则 | 3/4 条订阅条目 |
| mihomo | **不合并**：每行规则 = 单个匹配动作；自定义列表已经用 rule-provider 合并。把上游 geosite 集也合并成自托管文件会失去上游自动更新，不建议 | 保持逐行 |
| Throne 订阅 | 保持结构化规则组和内置规则集引用 | 8/9 条 |

sing-box 默认规则的目的域名条件和目的 IP 条件属于同一个 OR 组，目的端口等其它条件还需同时满足。原生 `geoip`、`geosite` 字段已在 1.12 移除，订阅中同名的 `rule_set` 标签仍可使用。对于只带域名的连接，GeoIP 只有在路由阶段获得目标 IP 后才能匹配，例如先执行 `resolve`。对于只带 IP 的连接，域名规则需要通过 `sniff` 或 DNS 映射获得域名。mihomo 的 IP provider 规则带 `no-resolve`，只检查已有的目标 IP。
[sing-box 路由规则](https://sing-box.sagernet.org/configuration/route/rule/#default-fields) · [规则动作](https://sing-box.sagernet.org/configuration/route/rule_action/) · [mihomo no-resolve](https://wiki.metacubex.one/en/config/rules/#no-resolve)

## v2rayN 7.25.6+ 接入

1. **完整配置模板**。把 `sing-box/*.json` 里的顶层 `http_clients` 与 `route` 按需并入模板，和现有 DNS、进程规则一起调整顺序。把 `out-ai` 对齐到模板中的出站标签。补全 `inbounds` 和 `outbounds` 后也可以通过「自定义配置」加载。
2. **GUI 路由订阅**。在规则集设置的「可选地址 (Url)」填写 `https://proxy-route.shkits.com/v2rayN/smartroute-proxy-list-out-ai.rules.json`（或 CN whitelist 版），点击「从订阅 Url 中导入规则」。曾配置自定义规则集映射的用户，迁移时请清空「自定义 sing-box rule set」字段。
   - **sing-box 内核**优先加载 v2rayN 数据目录 `bin/srss` 中按 tag 命名的 SRS。放入 [geoip-openai.srs](https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-openai.srs)；标准类别由 v2rayN 自带下载器处理。要与本订阅使用完全相同的规则集，将 `sing-box/*.json` 里 `route.rule_set` 的各 URL 下载到该目录，按 `<tag>.srs` 命名。 [v2rayN 规则集加载源码](https://github.com/2dust/v2rayN/blob/7.25.6/v2rayN/ServiceLib/Services/CoreConfig/Singbox/SingboxRulesetService.cs)
   - **Xray 内核**使用包含 `OPENAI`、`GOOGLE` 和 `TELEGRAM` 的完整版 `geoip.dat`，以及包含订阅各域名类别的扩展 `geosite.dat`。IP 数据可以使用 [Chocolate4U 的完整版 geoip.dat](https://github.com/Chocolate4U/Iran-v2ray-rules/releases/latest/download/geoip.dat)。

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

脚本只读打开 `throne.db`，在导出时把 `geosite-google` 加入两套策略引用 `geoip-google` 的 `out-ai` 规则组。重新导出只清理生成子目录（`sing-box/mihomo/v2rayN/lists/throne`）。
