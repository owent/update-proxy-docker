#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Throne route profiles (SmartRoute ai-bb) into URL-subscribable formats.

Usage: python -I export_throne_routes.py [output_dir]
Default output_dir: ./throne-route-export next to the parent of this script.

Reads D:/program/Throne/config/throne.db (read-only) and emits:
  <out>/
    sing-box/smartroute-*.json      route fragment (rules + remote rule_set + final)
    sing-box/rule-set-src/*.json    custom lists as sing-box source rule-sets (hostable)
    mihomo/smartroute-*.yaml        rules + rule-providers fragment
    mihomo/providers/*.yaml         custom lists as mihomo rule-providers (hostable)
    v2rayN/smartroute-*.rules.json  v2rayN 自定义路由规则数组（可从 URL 订阅导入）
    v2rayN/singbox-custom-ruleset.json  v2rayN 自定义 sing-box rule set 映射
    throne/smartroute-*.txt         Throne 路由订阅文件（throne://route/ deeplink，一行）
    throne/add-both-remote.txt      throne://remoteroute/ 一次性订阅两条路由的 deeplink
    lists/*.txt                     plain text lists

Outbound placeholders (NO credentials are exported):
  Throne -2 -> direct        (直连)
  Throne -1 -> proxy         (主出站)
  Throne 15 -> out-ai        (vr-us-bb.shkits.com(AnyTLS) 节点 tag；用户本机 v2rayN 模板中对应 out-proxy-ai)
  Throne 分享格式中 out-ai 按节点名解析（导入端需存在同名节点，否则回退 proxy 并警告）

githubusercontent.com 可达性：sing-box rule_set 已带 download_detour=proxy；
mihomo 指向 raw.githubusercontent.com 的 provider 附 proxy: PROXY；Throne 拉取订阅时自动改写 jsdelivr。
"""
import base64
import json
import pathlib
import shutil
import sqlite3
import sys

DB_URI = r"file:D:/program/Throne/config/throne.db?mode=ro"
HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "routes"
OUT_ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUT

# 发布站点（GitHub Pages 自定义域名）
SITE = "https://proxy-route.shkits.com"

PROFILE_IDS = {6: "smartroute-cn-whitelist-out-ai", 7: "smartroute-proxy-list-out-ai"}

SING = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo"
META = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo"
# Throne 内置 rule-set 名称 -> (sing-box .srs URL, mihomo .yaml URL)
# mihomo 的 geoip-openai 在 MetaCubeX 无对应集合，改用 ipinfo 的 ai 类别(含 OpenAI 等)
RULESETS = {
    "geoip-private":             (f"{SING}/geoip/private.srs",             f"{META}/geoip/private.yaml"),
    "geoip-cn":                  (f"{SING}/geoip/cn.srs",                  f"{META}/geoip/cn.yaml"),
    "geoip-google":              (f"{SING}/geoip/google.srs",              f"{META}/geoip/google.yaml"),
    "geoip-openai":              ("https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-openai.srs",
                                  f"{META}/geoip/ai.yaml"),
    "geoip-telegram":            (f"{SING}/geoip/telegram.srs",            f"{META}/geoip/telegram.yaml"),
    "geosite-cn":                (f"{SING}/geosite/cn.srs",                f"{META}/geosite/cn.yaml"),
    "geosite-category-speedtest":(f"{SING}/geosite/category-speedtest.srs", f"{META}/geosite/category-speedtest.yaml"),
    "geosite-codeberg":          (f"{SING}/geosite/codeberg.srs",          f"{META}/geosite/codeberg.yaml"),
    "geosite-category-dev-cn":   (f"{SING}/geosite/category-dev-cn.srs",   f"{META}/geosite/category-dev-cn.yaml"),
    "geosite-anthropic":         (f"{SING}/geosite/anthropic.srs",         f"{META}/geosite/anthropic.yaml"),
    "geosite-category-ai-!cn":   (f"{SING}/geosite/category-ai-!cn.srs",   f"{META}/geosite/category-ai-!cn.yaml"),
    "geosite-unity":             (f"{SING}/geosite/unity.srs",             f"{META}/geosite/unity.yaml"),
    "geosite-gfw":               (f"{SING}/geosite/gfw.srs",               f"{META}/geosite/gfw.yaml"),
    "geosite-geolocation-!cn":   (f"{SING}/geosite/geolocation-!cn.srs",   f"{META}/geosite/geolocation-!cn.yaml"),
}

OUTBOUND_MAP = {-2: "direct", -1: "proxy", 15: "out-ai"}
MIHOMO_OUT = {"direct": "DIRECT", "proxy": "PROXY", "out-ai": "out-ai"}
V2RAYN_OUT = {"direct": "direct", "proxy": "proxy", "out-ai": "out-ai"}


def open_db():
    con = sqlite3.connect(DB_URI, uri=True)
    con.row_factory = sqlite3.Row
    return con


def load_profiles(con):
    profiles = {}
    for pid in PROFILE_IDS:
        row = con.execute("SELECT * FROM route_profiles WHERE id=?", (pid,)).fetchone()
        rules = con.execute(
            "SELECT * FROM route_rules WHERE route_profile_id=? ORDER BY rule_order ASC",
            (pid,),
        ).fetchall()
        profiles[pid] = {"meta": dict(row), "rules": [dict(r) for r in rules]}
    return profiles


def jload(col):
    return json.loads(col) if col else []


def collect_used_rulesets(profiles):
    used = {}
    for p in profiles.values():
        for r in p["rules"]:
            for name in jload(r["rule_set_json"]):
                used[name] = True
    return used


def _match_groups(profile):
    """把 Throne 规则按出站分段（跳过 hijack-dns），段内归并各类匹配器。

    只合并相邻且同出站的规则 —— 保证与逐条形式严格等价。
    返回 [(outbound, name_label, {match_type: [values]})]。
    """
    runs = []
    for r in profile["rules"]:
        if r["action"] == "hijack-dns":
            continue
        out = OUTBOUND_MAP[r["outbound_id"]]
        m = {}
        for name in jload(r["rule_set_json"]):
            m.setdefault("rule_set", []).append(name)
        for col, key in (
            ("domain_suffix_json", "domain_suffix"),
            ("domain_keyword_json", "domain_keyword"),
            ("domain_regex_json", "domain_regex"),
        ):
            vals = jload(r[col])
            if vals:
                m.setdefault(key, []).extend(vals)
        if runs and runs[-1][0] == out:
            _, label, prev = runs[-1]
            for k, v in m.items():
                prev.setdefault(k, []).extend(v)
            runs[-1] = (out, label + "+" + r["name"], prev)
        else:
            runs.append((out, r["name"], m))
    return runs


def build_singbox(profile):
    used = {}
    rules = [{"protocol": "dns", "action": "hijack-dns"}]
    for out, _label, m in _match_groups(profile):
        for name in m.get("rule_set", []):
            used[name] = True
        # sing-box 单条规则内不同字段是 AND，需用 logical or 包裹才能合并
        sub = [{k: v} for k, v in m.items()]
        rules.append({"type": "logical", "mode": "or", "rules": sub, "outbound": out})
    rule_set = [
        {
            "type": "remote",
            "tag": name,
            "format": "binary",
            "url": RULESETS[name][0],
            "download_detour": "proxy",
        }
        for name in used
    ]
    final = OUTBOUND_MAP[profile["meta"]["default_outbound_id"]]
    return {
        "route": {
            "rules": rules,
            "rule_set": rule_set,
            "final": final,
        }
    }


def custom_lists(profile):
    """Extract the three custom (non-rule-set) lists by rule name."""
    out = {}
    for r in profile["rules"]:
        if r["name"] == "私有域名(域名后缀)":
            out["direct_private_suffix"] = jload(r["domain_suffix_json"])
        elif r["name"] == "私有域名(正则)":
            out["direct_private_regex"] = jload(r["domain_regex_json"])
        elif r["name"] == "AI-关键字":
            out["ai_keywords"] = jload(r["domain_keyword_json"])
        elif r["name"] == "特殊 US 链路":
            out["us_suffix"] = jload(r["domain_suffix_json"])
    return out


def write_rule_set_src(lists):
    d = OUT_ROOT / "sing-box" / "rule-set-src"
    d.mkdir(parents=True, exist_ok=True)
    direct_private = {
        "version": 1,
        "rules": [
            {
                "domain_suffix": lists["direct_private_suffix"],
                "domain_regex": lists["direct_private_regex"],
            }
        ],
    }
    ai_kw = {"version": 1, "rules": [{"domain_keyword": lists["ai_keywords"]}]}
    us = {"version": 1, "rules": [{"domain_suffix": lists["us_suffix"]}]}
    for name, obj in (
        ("direct-private.json", direct_private),
        ("out-ai-keywords.json", ai_kw),
        ("out-ai-domains.json", us),
    ):
        (d / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def write_mihomo_providers(lists):
    d = OUT_ROOT / "mihomo" / "providers"
    d.mkdir(parents=True, exist_ok=True)
    lines_dp = ["payload:"]
    lines_dp += [f"  - DOMAIN-SUFFIX,{x}" for x in lists["direct_private_suffix"]]
    lines_dp += [f"  - DOMAIN-REGEX,{x}" for x in lists["direct_private_regex"]]
    lines_kw = ["payload:"] + [f"  - DOMAIN-KEYWORD,{x}" for x in lists["ai_keywords"]]
    lines_us = ["payload:"] + [f"  - DOMAIN-SUFFIX,{x}" for x in lists["us_suffix"]]
    for name, lines in (
        ("direct-private.yaml", lines_dp),
        ("out-ai-keywords.yaml", lines_kw),
        ("out-ai-domains.yaml", lines_us),
    ):
        (d / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_lists_txt(lists):
    d = OUT_ROOT / "lists"
    d.mkdir(parents=True, exist_ok=True)
    files = {
        "direct-private-suffix.txt": lists["direct_private_suffix"],
        "direct-private-regex.txt": lists["direct_private_regex"],
        "out-ai-keywords.txt": lists["ai_keywords"],
        "out-ai-domains.txt": lists["us_suffix"],
    }
    for name, items in files.items():
        (d / name).write_text("\n".join(items) + "\n", encoding="utf-8")


def build_mihomo(profile):
    providers = {
        # 自定义列表：已直接指向发布站点
        "direct-private": {
            "behavior": "classical",
            "url": f"{SITE}/mihomo/providers/direct-private.yaml",
        },
        "out-ai-keywords": {
            "behavior": "classical",
            "url": f"{SITE}/mihomo/providers/out-ai-keywords.yaml",
        },
        "out-ai-domains": {
            "behavior": "classical",
            "url": f"{SITE}/mihomo/providers/out-ai-domains.yaml",
        },
    }
    # Throne 规则名 -> 自定义 provider tag（正则规则并入后缀规则所在 provider，两者出站相同且相邻）
    custom_provider = {
        "私有域名(域名后缀)": ("direct-private", "私有域名(后缀+正则)"),
        "私有域名(正则)": None,
        "AI-关键字": ("out-ai-keywords", "AI-关键字"),
        "特殊 US 链路": ("out-ai-domains", "特殊 US 链路"),
    }
    rules = ["# DNS 劫持由 mihomo 的 TUN/DNS 模块处理，无需等价规则"]
    for r in profile["rules"]:
        if r["action"] == "hijack-dns":
            continue
        out = MIHOMO_OUT[OUTBOUND_MAP[r["outbound_id"]]]
        comment = f"  # {r['name']}"
        first = True
        cp = custom_provider.get(r["name"], False)
        if cp is not False:
            if cp:
                tag, label = cp
                rules.append(f"- RULE-SET,{tag},{out}  # {label}")
            continue
        for name in jload(r["rule_set_json"]):
            if name == "geoip-openai":
                note = "  # Throne 原集合 geoip-openai(仅 sing-box 格式)，此处用 ipinfo ai 类别替代"
            else:
                note = comment if first else None
            is_ip = name.startswith("geoip-")
            line = f"- RULE-SET,{name},{out}" + (",no-resolve" if is_ip else "")
            rules.append(line + (note or ""))
            if name not in providers:
                providers[name] = {
                    "behavior": "ipcidr" if is_ip else "domain",
                    "url": RULESETS[name][1],
                    # githubusercontent 直连不可达时的下载代理（占位符，同 PROXY 出站）
                    "proxy": "PROXY" if "raw.githubusercontent.com" in RULESETS[name][1] else None,
                }
            first = False
        for col, fmt in (
            ("domain_suffix_json", "DOMAIN-SUFFIX"),
            ("domain_keyword_json", "DOMAIN-KEYWORD"),
            ("domain_regex_json", "DOMAIN-REGEX"),
        ):
            for v in jload(r[col]):
                rules.append(f"- {fmt},{v},{out}" + (comment if first else ""))
                first = False
    final = MIHOMO_OUT[OUTBOUND_MAP[profile["meta"]["default_outbound_id"]]]
    rules.append(f"- MATCH,{final}")

    out = ["rules:"]
    out += [f"  {x}" for x in rules]
    out.append("")
    out.append("rule-providers:")
    for tag, p in providers.items():
        out.append(f'  "{tag}":')
        out.append("    type: http")
        out.append(f"    behavior: {p['behavior']}")
        out.append("    format: yaml")
        out.append(f'    url: "{p["url"]}"')
        out.append(f"    path: ./ruleset/{tag}.yaml")
        out.append("    interval: 86400")
        if p.get("proxy"):
            out.append(f"    proxy: {p['proxy']}  # raw.githubusercontent.com 需经代理下载；不需要可删")
    return "\n".join(out) + "\n"


def build_v2rayn_rules(profile):
    """v2rayN 自定义路由规则数组（Xray 风格；数组内 OR 语义，相邻同出站已合并为单条）。"""
    # geoip.dat(Loyalsoldier 扩展版) 里没有 openai 类别，只有 sing-box ruleset 能解析
    geoip_dat_note = {"openai": "；geoip:openai 需 sing-box 内核+自定义 ruleset"}
    entries = []
    for out, label, m in _match_groups(profile):
        out = V2RAYN_OUT[out]
        entry = {"outboundTag": out, "enabled": True, "remarks": label}
        if m.get("rule_set"):
            domain, ip = [], []
            for rs in m["rule_set"]:
                if rs.startswith("geoip-"):
                    cat = rs[len("geoip-"):]
                    ip.append(f"geoip:{cat}")
                    if cat in geoip_dat_note:
                        entry["remarks"] += geoip_dat_note[cat]
                else:
                    domain.append(f"geosite:{rs[len('geosite-'):]}")
            if domain:
                entry["domain"] = domain
            if ip:
                entry["ip"] = ip
        # Xray domain 数组：domain: 前缀=后缀匹配，裸字符串=子串匹配，regexp:=正则
        if m.get("domain_suffix"):
            entry.setdefault("domain", []).extend(f"domain:{x}" for x in m["domain_suffix"])
        if m.get("domain_keyword"):
            entry.setdefault("domain", []).extend(m["domain_keyword"])
        if m.get("domain_regex"):
            entry.setdefault("domain", []).extend(f"regexp:{x}" for x in m["domain_regex"])
        entries.append(entry)
    final = V2RAYN_OUT[OUTBOUND_MAP[profile["meta"]["default_outbound_id"]]]
    entries.append(
        {"port": "0-65535", "outboundTag": final, "enabled": True, "remarks": "最终"}
    )
    return entries


def write_v2rayn(profiles, used_rulesets):
    d = OUT_ROOT / "v2rayN"
    d.mkdir(parents=True, exist_ok=True)
    for pid, slug in PROFILE_IDS.items():
        (d / f"{slug}.rules.json").write_text(
            json.dumps(build_v2rayn_rules(profiles[pid]), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
    # 自定义 sing-box rule set：tag -> 与 Throne 相同的 .srs 源
    ruleset = [
        {
            "tag": name,
            "type": "remote",
            "format": "binary",
            "url": RULESETS[name][0],
            "download_detour": "proxy",
        }
        for name in used_rulesets
    ]
    (d / "singbox-custom-ruleset.json").write_text(
        json.dumps(ruleset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _throne_outbound_name(con, outbound_id):
    """Throne 分享格式的出站引用：-1/-2 为 proxy/direct，正数按本机节点名解析。"""
    if outbound_id == -1:
        return "proxy"
    if outbound_id == -2:
        return "direct"
    row = con.execute("SELECT name FROM profiles WHERE id=?", (outbound_id,)).fetchone()
    return row["name"] if row else "proxy"


def build_throne_share(con, profile):
    """Throne 路由分享对象（throne-route-profile v1，逐条形式）。"""
    rules = []
    for r in profile["rules"]:
        rule = {"type": "custom", "name": r["name"]}
        if r["action"] == "hijack-dns":
            rule["protocol"] = "dns"
            rule["action"] = "hijack-dns"
            rules.append(rule)
            continue
        for col, key in (
            ("domain_suffix_json", "domain_suffix"),
            ("domain_keyword_json", "domain_keyword"),
            ("domain_regex_json", "domain_regex"),
        ):
            vals = jload(r[col])
            if vals:
                rule[key] = vals
        if r["rule_set_json"]:
            rule["rule_set"] = jload(r["rule_set_json"])
        rule["action"] = "route"
        rule["outbound"] = _throne_outbound_name(con, r["outbound_id"])
        rules.append(rule)
    return {
        "kind": "throne-route-profile",
        "v": 1,
        "name": profile["meta"]["name"].replace("ai-bb", "out-ai"),
        "default_outbound": _throne_outbound_name(con, profile["meta"]["default_outbound_id"]),
        "rules": rules,
    }


def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def write_throne(con, profiles):
    d = OUT_ROOT / "throne"
    d.mkdir(parents=True, exist_ok=True)
    sub_urls = []
    for pid, slug in PROFILE_IDS.items():
        obj = build_throne_share(con, profiles[pid])
        compact = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        link = "throne://route/" + _b64url_nopad(compact.encode("utf-8"))
        (d / f"{slug}.txt").write_text(link + "\n", encoding="utf-8")
        # URL fragment 作为导入后的显示名（仅用 URL 安全字符）
        sub_urls.append(f"{SITE}/throne/{slug}.txt#{slug}")
    # 一次性把两条路由都加为远程订阅（throne://remoteroute/<b64url of URL 列表>）
    bundle = "\n".join(sub_urls)
    (d / "add-both-remote.txt").write_text(
        "throne://remoteroute/" + _b64url_nopad(bundle.encode("utf-8")) + "\n",
        encoding="utf-8",
    )
    return sub_urls


def main():
    con = open_db()
    profiles = load_profiles(con)
    lists = custom_lists(profiles[6])
    assert len(lists) == 4, "custom lists incomplete"
    used_rulesets = collect_used_rulesets(profiles)

    # 清理旧的生成内容（仅已知子目录；保留 index.md/CNAME/.nojekyll 等站点文件）
    for sub in ("sing-box", "mihomo", "v2rayN", "lists", "throne"):
        p = OUT_ROOT / sub
        if p.exists():
            shutil.rmtree(p)

    sb_dir = OUT_ROOT / "sing-box"
    mh_dir = OUT_ROOT / "mihomo"
    sb_dir.mkdir(parents=True)
    mh_dir.mkdir(parents=True)

    for pid, slug in PROFILE_IDS.items():
        frag = build_singbox(profiles[pid])
        (sb_dir / f"{slug}.json").write_text(
            json.dumps(frag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (mh_dir / f"{slug}.yaml").write_text(
            build_mihomo(profiles[pid]), encoding="utf-8"
        )
        print(f"profile {pid} -> {slug}.json / .yaml  "
              f"(rules={len(frag['route']['rules'])}, rule_set={len(frag['route']['rule_set'])}, "
              f"final={frag['route']['final']})")

    write_rule_set_src(lists)
    write_mihomo_providers(lists)
    write_lists_txt(lists)
    write_v2rayn(profiles, used_rulesets)
    throne_urls = write_throne(con, profiles)
    con.close()
    print("v2rayN -> *.rules.json + singbox-custom-ruleset.json (%d sets)" % len(used_rulesets))
    print("throne -> 订阅文件 x2 + add-both-remote.txt")
    for u in throne_urls:
        print("  ", u)
    print("done ->", OUT_ROOT)


if __name__ == "__main__":
    sys.exit(main())
