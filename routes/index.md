# 代理路由订阅

本站（`proxy-route.shkits.com`）托管从 Throne 导出的分流路由订阅，来源仓库 [`owent/update-proxy-docker`](https://github.com/owent/update-proxy-docker) 的 [`routes/`](https://github.com/owent/update-proxy-docker/tree/main/routes) 目录，main 分支变更后自动发布。

两条路由的区别：

- **CN whitelist（白名单模式）**：大陆/内网/私有域名直连，AI 及特殊域名走 `out-ai`，**其余全部走代理**
- **proxy list（代理名单模式）**：直连规则同上，GFW/Telegram/国外域名走主代理，**其余全部直连**

## 各工具订阅 URL

### Throne

| 路由 | 订阅 URL |
|---|---|
| CN whitelist | `https://proxy-route.shkits.com/throne/smartroute-cn-whitelist-out-ai.txt` |
| proxy list | `https://proxy-route.shkits.com/throne/smartroute-proxy-list-out-ai.txt` |

 Throne 中导入剪贴板/文件粘贴 deeplink，或把上面 URL 添加为远程路由配置（自动更新）。一次性订阅两条：[add-both-remote.txt](throne/add-both-remote.txt)。

### v2rayN（7.x，sing-box 内核）

| 内容 | URL |
|---|---|
| CN whitelist 路由规则 | `https://proxy-route.shkits.com/v2rayN/smartroute-cn-whitelist-out-ai.rules.json` |
| proxy list 路由规则 | `https://proxy-route.shkits.com/v2rayN/smartroute-proxy-list-out-ai.rules.json` |
| 自定义 sing-box rule set（14 个，建议一并配置） | `https://proxy-route.shkits.com/v2rayN/singbox-custom-ruleset.json` |

路由设置 → 导入规则 → **从订阅 URL 导入**；rule set 映射填到路由设置的「自定义 sing-box rule set」。

### mihomo / Clash Meta / Clash Verge

| 内容 | URL |
|---|---|
| CN whitelist 规则片段 | [smartroute-cn-whitelist-out-ai.yaml](mihomo/smartroute-cn-whitelist-out-ai.yaml) |
| proxy list 规则片段 | [smartroute-proxy-list-out-ai.yaml](mihomo/smartroute-proxy-list-out-ai.yaml) |
| direct-private provider | `https://proxy-route.shkits.com/mihomo/providers/direct-private.yaml` |
| out-ai-keywords provider | `https://proxy-route.shkits.com/mihomo/providers/out-ai-keywords.yaml` |
| out-ai-domains provider | `https://proxy-route.shkits.com/mihomo/providers/out-ai-domains.yaml` |

把片段里的 `rules` + `rule-providers` 合并进配置即可（providers 已直接指向本站）。

### sing-box

| 内容 | URL |
|---|---|
| CN whitelist route 片段 | [smartroute-cn-whitelist-out-ai.json](sing-box/smartroute-cn-whitelist-out-ai.json) |
| proxy list route 片段 | [smartroute-proxy-list-out-ai.json](sing-box/smartroute-proxy-list-out-ai.json) |
| direct-private rule-set（source 格式） | `https://proxy-route.shkits.com/sing-box/rule-set-src/direct-private.json` |
| out-ai-keywords rule-set（source 格式） | `https://proxy-route.shkits.com/sing-box/rule-set-src/out-ai-keywords.json` |
| out-ai-domains rule-set（source 格式） | `https://proxy-route.shkits.com/sing-box/rule-set-src/out-ai-domains.json` |

### 其他工具（AdGuard / dnsmasq / SwitchyOmega 等）

纯文本列表：[lists/](lists/)（direct-private-suffix / direct-private-regex / out-ai-keywords / out-ai-domains）。

## 两个占位出站

规则里 `proxy`（主出站）和 `out-ai`（AI 专用出站，原 Throne 节点 `vr-us-bb.shkits.com(AnyTLS)`）是**引用名，不含凭据**，各工具在自己配置里绑定实际节点：

- sing-box / Throne：`outbounds` 里定义 `"tag": "out-ai"` 的出站
- mihomo：建名为 `out-ai` 的策略组
- v2rayN 路由规则：outboundTag 直接填节点/策略组名（Throne 导入则按节点名 `vr-us-bb.shkits.com(AnyTLS)` 解析，本机需存在同名节点，否则回退 proxy）

## 关于 raw.githubusercontent.com 下载

公共 geosite/geoip 规则集仍托管在 raw.githubusercontent.com，导出配置已内置三层保障：

1. **sing-box / v2rayN**：rule_set 带 `download_detour: "proxy"`（经代理下载）
2. **mihomo**：对应 rule-provider 带 `proxy: PROXY`（经代理下载，按需改成你的组名）
3. **无代理环境**：把 URL 换成 jsdelivr 镜像即可，如
   `https://cdn.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@sing/geo/geoip/cn.srs`；
   Throne 自身拉取 githubusercontent 订阅时会自动改写为 jsdelivr。

更多细节见 [README.md](README.md)。
