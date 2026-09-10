#!/usr/bin/env python3
"""
API 测试报告生成器
==================
从 allure-results/*.json 生成轻量单 HTML 测试报告。
内置 CSS/JS 渲染，无需外部依赖。

用法:
    python utils/report_generator.py
    python utils/report_generator.py --input allure-results --output allure-report/report.html
"""

import json, os, sys, glob, hashlib, base64, gzip, io, html as _html, shutil
from pathlib import Path


def read_text(path):
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f: return f.read()
        except (UnicodeDecodeError, UnicodeError): continue
        except: return ""
    return ""

def read_binary(path):
    try:
        with open(path, "rb") as f: return f.read()
    except: return b""

_uid_counter = 0

def _reset_uids():
    global _uid_counter
    _uid_counter = 0

def uid():
    """Return a deterministic report-local ID instead of a random UUID."""
    global _uid_counter
    _uid_counter += 1
    return f"tcli-{_uid_counter:016x}"

def write_text_if_changed(path, content):
    """Keep this standalone template from rewriting byte-identical reports."""
    output = Path(path)
    try:
        if output.read_text(encoding="utf-8") == content:
            return False
    except OSError:
        pass
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return True

def compress_deterministically(data):
    """Create gzip bytes without embedding the current wall-clock time."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0, compresslevel=9) as stream:
        stream.write(data)
    return buffer.getvalue()

_TEXT_MIMES = {"text/", "application/json", "application/xml", "application/javascript", "application/csv"}
def is_text_mime(mime):
    """判断 MIME 类型是否为文本（可安全用 read_text 读取）"""
    if not mime: return True
    if mime.startswith("text/"): return True
    return mime in _TEXT_MIMES

def read_attachment(path, mime):
    """根据 MIME 类型读取附件，返回 (content_for_D, size)"""
    if is_text_mime(mime):
        content = read_text(path)
        return content, len(content.encode("utf-8")) if content else 0
    else:
        data = read_binary(path)
        if data:
            b64 = base64.b64encode(data).decode("ascii")
            return f"data:{mime};base64,{b64}", len(data)
        return "", 0

def att_ext(mime):
    """根据 MIME 类型返回附件文件扩展名"""
    if mime == "application/json": return ".json"
    if mime == "image/png": return ".png"
    if mime == "image/jpeg": return ".jpg"
    if mime == "application/pdf": return ".pdf"
    return ".txt"

def gl(r, name):
    for lb in r.get("labels", []):
        if lb.get("name") == name: return lb.get("value", "")
    return ""

def load_results(d):
    rs = []
    for fp in sorted(glob.glob(os.path.join(d, "*-result.json"))):
        try:
            with open(fp, "r", encoding="utf-8") as f: rs.append(json.load(f))
        except: pass
    return rs

def load_containers(d):
    """加载 container.json，返回 {child_uuid: [container, ...]} 映射（一个用例可能关联多个 container）"""
    mapping = {}
    for fp in sorted(glob.glob(os.path.join(d, "*-container.json"))):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                c = json.load(f)
            for child in c.get("children", []):
                mapping.setdefault(child, []).append(c)
        except: pass
    return mapping

def short_hash(name):
    """生成 allure 风格的短哈希文件名"""
    return hashlib.md5(name.encode()).hexdigest()[:16]

def make_stage(item):
    """把 container 的 before/after 项转成 allure stage 格式"""
    return {
        "name": item.get("name", ""),
        "time": {"start": item.get("start", 0), "stop": item.get("stop", 0),
                 "duration": item.get("stop", 0) - item.get("start", 0)},
        "status": item.get("status", "passed"),
        "steps": [], "attachments": [], "parameters": [],
        "shouldDisplayMessage": False, "stepsCount": 0,
        "attachmentsCount": 0, "hasContent": False, "attachmentStep": False,
    }

def stat(rs):
    return {"failed": sum(1 for r in rs if r.get("status")=="failed"),
            "broken": sum(1 for r in rs if r.get("status")=="broken"),
            "skipped": sum(1 for r in rs if r.get("status")=="skipped"),
            "passed": sum(1 for r in rs if r.get("status")=="passed"),
            "unknown": sum(1 for r in rs if r.get("status") not in ("passed","failed","broken","skipped")),
            "total": len(rs)}

_exec_order = {}  # uuid -> execution order number

def leaf(r):
    return {"name":r.get("name",""),"uid":r.get("uuid") or uid(),"parentUid":"",
            "status":r.get("status","unknown"),"order":_exec_order.get(r.get("uuid"),0),
            "time":{"start":r.get("start",0),"stop":r.get("stop",0),"duration":r.get("stop",0)-r.get("start",0)},
            "flaky":False,"newFailed":False,"newPassed":False,"newBroken":False,
            "retriesCount":0,"retriesStatusChange":False,"parameters":[],"tags":[]}

def test_item(r):
    return {"uid":r.get("uuid") or uid(),"name":r.get("name",""),
            "time":{"start":r.get("start",0),"stop":r.get("stop",0),"duration":r.get("stop",0)-r.get("start",0)},
            "status":r.get("status","unknown"),"severity":gl(r,"severity") or "normal"}

def test_case(r, results_dir, containers=None, source_map=None):
    """source_map: {原始source: 短哈希source} 映射，同时用于重命名 data/attachments key"""
    if source_map is None: source_map = {}

    def _process_step(step):
        atts = []
        for att in step.get("attachments", []):
            src = att.get("source", "")
            mime = att.get("type", "text/plain")
            _, sz = read_attachment(os.path.join(results_dir, src), mime)
            new_src = short_hash(src) + att_ext(mime)
            source_map[src] = new_src
            atts.append({"uid":short_hash(src),"name":att.get("name",""),"source":new_src,
                         "type":mime,"size":sz})
        step_sd = step.get("statusDetails", {}) or {}
        sub_steps = [_process_step(s) for s in step.get("steps", []) if isinstance(s, dict)]
        return {"name":step.get("name",""),
                "time":{"start":step.get("start",0),"stop":step.get("stop",0),"duration":step.get("stop",0)-step.get("start",0)},
                "status":step.get("status","passed"),
                "statusMessage":step_sd.get("message",""),"statusTrace":step_sd.get("trace",""),
                "steps":sub_steps,"attachments":atts,"parameters":[],
                "shouldDisplayMessage":bool(step_sd.get("message")),"stepsCount":len(sub_steps),"attachmentsCount":len(atts),
                "hasContent":bool(atts) or bool(sub_steps),"attachmentStep":False}

    steps = [_process_step(step) for step in r.get("steps", []) if isinstance(step, dict)]
    sd = r.get("statusDetails", {})
    t_uid = r.get("uuid") or uid()
    fn = r.get("fullName", r.get("name", ""))
    desc = r.get("description", "")
    desc_html = f"<p>{_html.escape(desc)}</p>" if desc else ""

    # beforeStages / afterStages from containers（合并所有关联的 container）
    before_stages = []
    after_stages = []
    if containers:
        container_list = containers.get(t_uid, [])
        for container in container_list:
            before_stages.extend([make_stage(b) for b in container.get("befores", [])])
            after_stages.extend([make_stage(a) for a in container.get("afters", [])])

    # testStage 顶层附件（来自 result.json 的顶层 attachments，如 log、手动 attach 的内容）
    top_attachments = []
    log_attachments = []
    LOG_NAME_PATTERNS = ("log", "Log", "LOG", "standard", "stdout", "stderr", "output")
    for att in r.get("attachments", []):
        src = att.get("source", "")
        mime = att.get("type", "text/plain")
        _, sz = read_attachment(os.path.join(results_dir, src), mime)
        new_src = short_hash(src) + att_ext(mime)
        source_map[src] = new_src
        att_obj = {"uid":short_hash(src),"name":att.get("name",""),"source":new_src,
                   "type":mime,"size":sz}
        if any(p in (att.get("name","") + src) for p in LOG_NAME_PATTERNS) and mime.startswith("text/"):
            log_attachments.append(att_obj)
        else:
            top_attachments.append(att_obj)

    step_att_count = sum(len(s["attachments"]) for s in steps)
    total_att_count = step_att_count + len(top_attachments) + len(log_attachments)

    return {"uid":t_uid,"name":r.get("name",""),"fullName":fn,
            "historyId":r.get("historyId",hashlib.md5(fn.encode()).hexdigest()),
            "time":{"start":r.get("start",0),"stop":r.get("stop",0),"duration":r.get("stop",0)-r.get("start",0)},
            "description":desc,"descriptionHtml":desc_html,
            "status":r.get("status","unknown"),"statusMessage":sd.get("message",""),"statusTrace":sd.get("trace",""),
            "flaky":False,"newFailed":False,"newBroken":False,"newPassed":False,
            "retriesCount":0,"retriesStatusChange":False,
            "beforeStages":before_stages,"testStage":{"description":desc,"status":r.get("status","unknown"),
            "steps":steps,"attachments":top_attachments,"logAttachments":log_attachments,
            "parameters":r.get("parameters",[]),"shouldDisplayMessage":bool(sd.get("message")),
            "stepsCount":len(steps),"attachmentsCount":total_att_count,
            "hasContent":bool(steps) or bool(top_attachments) or bool(log_attachments),"attachmentStep":False},
            "afterStages":after_stages,"labels":r.get("labels",[]),"parameters":r.get("parameters",[]),
            "links":r.get("links",[]),"hidden":False,"retry":False,
            "extra":{"severity":gl(r,"severity") or "normal","retries":[],"categories":[],
                     "tags":[lb["value"] for lb in r.get("labels",[]) if lb.get("name")=="tag"]},
            "source":f"{t_uid}.json","parameterValues":[p.get("value","") for p in r.get("parameters",[])]}

def behaviors_tree(results):
    feats = {}
    for r in results:
        f = gl(r,"feature") or "未分组"
        s = gl(r,"story") or "默认"
        feats.setdefault(f,{}).setdefault(s,[]).append(r)
    ch = []
    for fn in sorted(feats):
        sch = [{"name":sn,"children":[leaf(r) for r in ts],"uid":uid()} for sn,ts in sorted(feats[fn].items())]
        ch.append({"name":fn,"children":sch,"uid":uid()})
    return {"uid":uid(),"name":"behaviors","children":ch}

def suites_tree(results):
    suites = {}
    for r in results:
        s1 = gl(r,"parentSuite") or "tests"
        s2 = gl(r,"suite") or "default"
        s3 = gl(r,"subSuite") or ""
        suites.setdefault(s1,{}).setdefault(s2,{}).setdefault(s3,[]).append(r)
    ch = []
    for s1 in sorted(suites):
        s2ch = []
        for s2 in sorted(suites[s1]):
            s3ch = []
            for s3 in sorted(suites[s1][s2]):
                leaves = [leaf(r) for r in suites[s1][s2][s3]]
                if s3: s3ch.append({"name":s3,"children":leaves,"uid":uid()})
                else: s3ch.extend(leaves)
            s2ch.append({"name":s2,"children":s3ch,"uid":uid()})
        ch.append({"name":s1,"children":s2ch,"uid":uid()})
    return {"uid":uid(),"name":"suites","children":ch}

def timeline_tree(results):
    threads = {}
    for r in results:
        h = gl(r,"host") or "unknown-host"
        t = gl(r,"thread") or "main"
        threads.setdefault(h,{}).setdefault(t,[]).append(r)
    ch = []
    for h in sorted(threads):
        tch = [{"name":t,"children":[leaf(r) for r in ts],"uid":uid()} for t,ts in sorted(threads[h].items())]
        ch.append({"name":h,"children":tch,"uid":uid()})
    return {"uid":uid(),"name":"timeline","children":ch}


def generate_report(results_dir="allure-results", output="allure-report/report.html", title=None, clean=False):
    _reset_uids()
    title = title or os.environ.get("REPORT_TITLE", "").strip() or f"{Path.cwd().name} API Test Report"
    output_path = Path(output)
    if clean and output_path.parent.exists():
        report_dir = output_path.parent.resolve()
        input_dir = Path(results_dir).resolve()
        if report_dir.name != "allure-report":
            raise ValueError("--clean 只允许清理名为 allure-report 的输出目录")
        if input_dir == report_dir or report_dir in input_dir.parents:
            raise ValueError("报告目录不能包含输入结果目录")
        shutil.rmtree(report_dir)
    results = load_results(results_dir)
    if not results:
        print(f"未找到: {results_dir}/*-result.json")
        sys.exit(1)
    results.sort(key=lambda r: (r.get("start", 0), r.get("uuid", ""), r.get("name", "")))
    global _exec_order
    _exec_order = {r.get("uuid"): i+1 for i, r in enumerate(results)}

    containers = load_containers(results_dir)
    print(f"读取 {len(results)} 个测试结果, {len(containers)} 个 container...")

    D = {}  # 所有数据文件

    # widgets
    starts = [r["start"] for r in results if r.get("start")]
    stops = [r["stop"] for r in results if r.get("stop")]
    durs = [r.get("stop",0)-r.get("start",0) for r in results if r.get("start") and r.get("stop")]
    D["widgets/summary.json"] = json.dumps({"reportName":title,"testRuns":[],
        "statistic":stat(results),"time":{"start":min(starts) if starts else 0,"stop":max(stops) if stops else 0,
        "duration":(max(stops)-min(starts)) if starts and stops else 0,
        "minDuration":min(durs) if durs else 0,"maxDuration":max(durs) if durs else 0,"sumDuration":sum(durs)}},ensure_ascii=False)

    items = [test_item(r) for r in results]
    D["widgets/status-chart.json"] = json.dumps(items, ensure_ascii=False)
    D["widgets/severity.json"] = json.dumps(sorted(items,key=lambda x:x["severity"]), ensure_ascii=False)
    D["widgets/duration.json"] = json.dumps(sorted(items,key=lambda x:x["time"]["duration"],reverse=True), ensure_ascii=False)
    D["widgets/categories.json"] = '{"total":0,"items":[]}'

    sg = {}
    for r in results:
        s = gl(r,"suite") or "default"
        sg.setdefault(s,[]).append(r)
    D["widgets/suites.json"] = json.dumps({"total":len(sg),
        "items":[{"uid":uid(),"name":k,"statistic":stat(v)} for k,v in sorted(sg.items())]},ensure_ascii=False)

    for k in ["launch","history-trend","categories-trend","duration-trend","retry-trend","executors"]:
        D[f"widgets/{k}.json"] = "[]"

    # environment widget — 读取 environment.properties
    env_file = os.path.join(results_dir, "environment.properties")
    env_data = []
    if os.path.exists(env_file):
        for line in read_text(env_file).strip().splitlines():
            if "=" in line:
                k_env, v_env = line.split("=", 1)
                env_data.append({"name": k_env.strip(), "values": [v_env.strip()]})
    D["widgets/environment.json"] = json.dumps(env_data, ensure_ascii=False)

    # categories — 读取 categories.json 并匹配用例
    import re as _re
    cat_file = os.path.join(results_dir, "categories.json")
    cat_rules = []
    if os.path.exists(cat_file):
        try:
            cat_rules = json.loads(read_text(cat_file))
        except: pass

    cat_children = []   # for data/categories.json tree
    cat_summary = {}     # for widgets/categories.json
    for rule in cat_rules:
        matched = []
        statuses = rule.get("matchedStatuses", [])
        msg_re = rule.get("messageRegex", "")
        trace_re = rule.get("traceRegex", "")
        for r in results:
            st = r.get("status", "")
            if statuses and st not in statuses:
                continue
            sd = r.get("statusDetails", {}) or {}
            msg = sd.get("message", "") or ""
            trace = sd.get("trace", "") or ""
            if msg_re and not _re.search(msg_re, msg, _re.IGNORECASE):
                if not trace_re:
                    continue
            if trace_re and not _re.search(trace_re, trace, _re.IGNORECASE):
                continue
            matched.append(r)
        if matched:
            cat_name = rule.get("name", "未分类")
            cat_children.append({"name": cat_name, "children": [leaf(r) for r in matched], "uid": uid()})
            cat_summary[cat_name] = stat(matched)

    if cat_summary:
        D["widgets/categories.json"] = json.dumps({
            "total": len(cat_summary),
            "items": [{"uid": uid(), "name": k, "statistic": v} for k, v in cat_summary.items()]
        }, ensure_ascii=False)
    else:
        # 无 categories.json 时，自动按状态生成默认分类
        demo_cats = {}
        for r in results:
            st = r.get("status", "unknown")
            if st == "failed":
                demo_cats.setdefault("Product Defects", []).append(r)
            elif st == "broken":
                demo_cats.setdefault("Test Defects", []).append(r)
        if demo_cats:
            cat_children = [{"name": k, "children": [leaf(r) for r in v], "uid": uid()} for k, v in demo_cats.items()]
            D["widgets/categories.json"] = json.dumps({
                "total": len(demo_cats),
                "items": [{"uid": uid(), "name": k, "statistic": stat(v)} for k, v in demo_cats.items()]
            }, ensure_ascii=False)

    # data trees
    D["data/behaviors.json"] = json.dumps(behaviors_tree(results), ensure_ascii=False)
    D["data/suites.json"] = json.dumps(suites_tree(results), ensure_ascii=False)
    D["data/packages.json"] = D["data/suites.json"]
    D["data/categories.json"] = json.dumps({"uid":uid(),"name":"categories","children":cat_children}, ensure_ascii=False)
    D["data/timeline.json"] = json.dumps(timeline_tree(results), ensure_ascii=False)

    # test cases + attachments（使用短哈希 source 名）
    source_map = {}  # {原始source: 短哈希source}
    for r in results:
        tc = test_case(r, results_dir, containers, source_map)
        D[f"data/test-cases/{tc['uid']}.json"] = json.dumps(tc, ensure_ascii=False)

    # 用短哈希名写入 attachments（支持文本和二进制）
    def _collect_atts(step_list, acc):
        for step in step_list:
            acc.extend(step.get("attachments", []))
            _collect_atts(step.get("steps", []), acc)
    for r in results:
        all_atts = []
        _collect_atts(r.get("steps", []), all_atts)
        all_atts.extend(r.get("attachments", []))
        for att in all_atts:
            src = att.get("source", "")
            if src and src in source_map:
                mime = att.get("type", "text/plain")
                content, _ = read_attachment(os.path.join(results_dir, src), mime)
                if content:
                    D[f"data/attachments/{source_map[src]}"] = content

    print(f"  生成 {len(D)} 个数据文件")

    dj = json.dumps(D, ensure_ascii=False, sort_keys=True)
    raw_size = len(dj.encode("utf-8"))
    compressed = compress_deterministically(dj.encode("utf-8"))
    b64 = base64.b64encode(compressed).decode("ascii")
    print(f"  压缩: {raw_size/1024/1024:.2f}MB -> {len(compressed)/1024/1024:.2f}MB ({len(compressed)/raw_size*100:.1f}%)")

    html = _build_html(b64, title)

    was_written = write_text_if_changed(output, html)

    sz = os.path.getsize(output) / 1024 / 1024
    p = sum(1 for r in results if r.get("status")=="passed")
    fl = sum(1 for r in results if r.get("status") in ("failed","broken"))
    s = sum(1 for r in results if r.get("status")=="skipped")
    print(f"报告{'已生成' if was_written else '内容未变化'}: {output} ({sz:.1f}MB)")
    print(f"结果: {p} passed / {fl} failed / {s} skipped (共 {len(results)} 个)")
    return output


# ---------------------------------------------------------------------------
#  轻量 HTML 模板
# ---------------------------------------------------------------------------

_CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --passed:#97cc64;--failed:#fd5a3e;--broken:#ffd050;--skipped:#aaa;--unknown:#d35ebe;
  --bg:#fff;--bg-page:#f8f8f9;--bg-hover:#e4edfe;--bg-active:#fffacd;
  --border:#eceff1;--border-dark:#e5e5e5;
  --text:#000;--text-secondary:#666;--text-muted:#999;
}
body{font:14px/1.5 Helvetica,Arial,sans-serif;color:var(--text);background:var(--bg);height:100vh;overflow:hidden}
a{color:inherit;text-decoration:none}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}

/* Header hidden - brand is in nav */
.header{display:none}

/* Layout: 3-panel (nav | tree | content) */
.main{display:flex;height:100vh}
.side-nav-col{flex-shrink:0;display:flex;flex-direction:column;height:100%}
.sidebar{width:340px;display:flex;flex-direction:column;overflow:hidden;background:var(--bg);border-right:1px solid var(--border);flex-shrink:0}
.sidebar.hidden{display:none}
.resizer{width:5px;background:var(--border) no-repeat 50%;cursor:ew-resize;flex-shrink:0}
.resizer:hover{background-color:#ccc}
.resizer.hidden{display:none}
.content{flex:1 1 auto;overflow:auto;position:relative}

/* Sidebar nav (Allure dark vertical - full height) */
.side-nav{background:linear-gradient(180deg,#3a3a3a 0%,#2d2d2d 100%);display:flex;flex-direction:column;padding:0;height:100%}
.side-nav-logo{display:flex;align-items:center;gap:10px;padding:20px 18px 18px;border-bottom:1px solid rgba(255,255,255,.1)}
.side-nav-logo .logo-text{color:#fff;font-size:20px;font-weight:800;letter-spacing:-.5px}
.side-nav-logo .logo-ver{color:rgba(255,255,255,.35);font-size:11px;font-weight:400}
.side-nav-item{display:flex;align-items:center;gap:12px;padding:13px 20px;cursor:pointer;font-size:13px;color:rgba(255,255,255,.55);transition:all .2s;border-left:3px solid transparent}
.side-nav-item:hover{color:rgba(255,255,255,.85);background:rgba(255,255,255,.06)}
.side-nav-item.active{color:#fff;background:rgba(255,255,255,.1);border-left-color:#64b5f6}
.side-nav-item svg{width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:2;flex-shrink:0}
.side-nav-footer{margin-top:auto;padding:14px 18px;border-top:1px solid rgba(255,255,255,.1);font-size:10px;color:rgba(255,255,255,.25);text-align:center;letter-spacing:.3px}

/* Tree controls */
.tree-ctrl{background:hsla(0,0%,94%,.15);border-bottom:1px solid var(--border);padding:6px 12px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.tree-marks{display:flex;gap:3px;flex-wrap:wrap}
.tree-strut{flex:1}
.tree-sorter{display:flex;gap:0;white-space:nowrap;color:var(--text-muted);user-select:none}

/* Marks (Allure y-label-mark / n-label-mark) */
.mark{display:inline-block;cursor:pointer;padding:1px 5px;border-radius:3px;letter-spacing:1px;font-size:12px;vertical-align:baseline}
.mark.on{color:#fff}
.mark.on.passed{background:var(--passed)}.mark.on.failed{background:var(--failed)}.mark.on.broken{background:var(--broken)}.mark.on.skipped{background:var(--skipped)}.mark.on.unknown{background:var(--unknown)}
.mark.off{border:1px solid;font-weight:700;background:transparent}
.mark.off.passed{color:var(--passed);border-color:var(--passed)}.mark.off.failed{color:var(--failed);border-color:var(--failed)}.mark.off.broken{color:var(--broken);border-color:var(--broken)}.mark.off.skipped{color:var(--skipped);border-color:var(--skipped)}

/* Sorter (Allure) */
.sort-item{display:inline-block;cursor:pointer;padding:2px 8px;font-size:12px;color:var(--text-muted)}
.sort-item:hover{color:var(--text)}
.sort-item .arr-up,.sort-item .arr-down{font-size:8px;line-height:1;display:block}
.sort-item .sort-arrows{display:inline-block;width:10px;vertical-align:middle;text-align:center}
.sort-item.asc .arr-up{color:var(--text)}.sort-item.desc .arr-down{color:var(--text)}

/* Search */
.tree-search{padding:6px 12px}
.tree-search input{width:100%;border:1px solid var(--border-dark);padding:4px 8px;font-size:13px;outline:none;font-family:inherit;border-radius:2px}
.tree-search input:focus{border-color:#64b5f6}

/* Tree body */
.tree-body{flex:1;overflow:auto}
.tree-body ul{list-style:none}
.tree-children{padding-left:16px}
.tree-children.collapsed{display:none}
.tree-row{display:flex;align-items:center;padding:5px 10px;cursor:pointer;font-size:13px;gap:5px;min-height:28px;color:var(--text);text-decoration:none;border-bottom:1px solid rgba(0,0,0,.03)}
.tree-row:hover{background:var(--bg-hover)}
.tree-row.active{background:var(--bg-active)}
.tree-toggle{width:12px;flex-shrink:0;font-size:9px;color:var(--text-muted);text-align:center;user-select:none}
.tree-num{font-size:11px;color:var(--text-muted);min-width:16px;text-align:right;flex-shrink:0}
.tree-icon{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.tree-icon.passed{background:var(--passed)}.tree-icon.failed{background:var(--failed)}.tree-icon.broken{background:var(--broken)}.tree-icon.skipped{background:var(--skipped)}.tree-icon.unknown{background:var(--unknown)}
.tree-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* color rows by status */
.tree-row.st-failed{background:#fff5f5}.tree-row.st-failed:hover{background:#ffe7e6}
.tree-row.st-broken{background:#fffdf5}.tree-row.st-broken:hover{background:#fff8e1}
.tree-mini{display:flex;align-items:center;gap:4px;flex-shrink:0}
.tree-mini-bar{display:flex;width:48px;height:5px;border-radius:3px;overflow:hidden;background:#e5e5e5}
.tree-mini-count{font-size:11px;color:var(--text-muted);min-width:24px;text-align:right}
.tree-dur{font-size:11px;color:var(--text-muted);flex-shrink:0}
/* Tree group/leaf hierarchy */
.tree-row.group{font-weight:600;font-size:13px;padding:7px 10px}
.tree-row.group .tree-icon{display:none}
.tree-row.group .tree-toggle{font-size:11px;color:var(--text-secondary)}
.tree-row.group .tree-num{display:none}
.tree-row.leaf{font-weight:400}

/* Expand/Collapse buttons */
.tree-expand-btns{display:flex;gap:2px;margin-left:8px}
.tree-expand-btns button{background:none;border:1px solid var(--border-dark);border-radius:3px;padding:1px 6px;font-size:11px;color:var(--text-muted);cursor:pointer;font-family:inherit;line-height:1.5}
.tree-expand-btns button:hover{background:var(--bg-hover);color:var(--text)}

/* Overview */
.overview{padding:28px 32px;max-height:100%;overflow:auto;background:var(--bg-page);max-width:1200px;margin:0 auto}
.ov-title{font-weight:600;font-size:24px;margin-bottom:4px;color:var(--text)}
.ov-sub{font-size:13px;color:var(--text-muted);margin-bottom:24px}
.widgets-grid{display:flex;flex-wrap:wrap;gap:0 24px}
.widgets-col{flex:1;min-width:300px;padding-right:0}
.widget{margin-bottom:20px;background:#fff;border-radius:8px;border:1px solid var(--border);padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.widget-title{font-weight:600;margin-bottom:14px;text-transform:uppercase;font-size:12px;color:var(--text-muted);letter-spacing:.5px}
.summary-flex{display:flex;gap:32px;align-items:flex-start}
.summary-chart{position:relative}
.summary-stats{padding-top:8px}
.stat-row{display:flex;align-items:center;gap:8px;margin-bottom:4px;font-size:14px;line-height:1.5}
.stat-icon{width:20px;height:16px;border-radius:3px;flex-shrink:0}
.stat-count{font-weight:700;min-width:20px}
.suite-row{display:flex;align-items:center;margin-bottom:6px;font-size:13px;gap:8px}
.suite-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.suite-bar{display:flex;width:120px;height:14px;overflow:hidden;flex-shrink:0}
.suite-count{width:24px;text-align:right;font-size:12px;color:var(--text-muted)}
.dur-row{display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px}
.dur-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px}
.dur-bar-wrap{flex:2;height:10px;background:#f2f2f2;overflow:hidden}
.dur-bar{height:100%;min-width:2px}
.dur-val{width:50px;text-align:right;font-size:12px;color:var(--text-muted)}
.env-table{width:100%;border-collapse:collapse;font-size:13px;border-top:1px solid var(--border)}
.env-table td,.env-table th{text-align:left;padding:8px 12px;border-bottom:1px solid var(--border)}
.env-table th{font-weight:700}.env-table tr:hover td{background:var(--bg-hover)}

/* Test case detail */
.tc-wrap{overflow:auto}
.tc-header{padding:14px 20px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border);background:var(--bg-page)}
.tc-title{font-size:18px;font-weight:700;line-height:1.3}
.badge{display:inline-block;padding:2px 8px;border-radius:3px;color:#fff;font-size:12px;font-weight:600;text-transform:capitalize}
.badge.passed{background:var(--passed)}.badge.failed{background:var(--failed)}.badge.broken{background:var(--broken)}.badge.skipped{background:var(--skipped)}.badge.unknown{background:var(--unknown)}
.tc-meta{padding:10px 20px;font-size:12px;color:var(--text-muted);border-bottom:1px solid var(--border);background:var(--bg-page)}
.tc-section{margin:16px 0;padding:0 20px}
.tc-section-title{font-weight:700;margin:0 0 8px;font-size:14px}
.status-details{margin-bottom:10px;overflow:auto;padding:12px;border-left:3px solid;border-radius:4px}
.status-details.s-failed{border-color:var(--failed);background:#ffe7e6}
.status-details.s-broken{border-color:var(--broken);background:#fffae6}
.tc-trace{margin-top:6px}
.tc-trace summary{cursor:pointer;font-size:12px;color:var(--text-muted)}
.tc-trace pre{font-size:11px;background:#f8f8f9;padding:8px;overflow:auto;white-space:pre-wrap;max-height:400px;margin-top:4px}
.step{padding:10px 14px;border:1px solid var(--border);border-radius:6px;margin-bottom:6px;background:#fff}
.step-hdr{display:flex;align-items:center;gap:8px;font-size:13px}
.step-badge{display:inline-block;padding:1px 6px;border-radius:3px;color:#fff;font-size:10px;font-weight:600;text-transform:uppercase;flex-shrink:0}
.step-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.step-dur{font-size:12px;color:var(--text-muted);flex-shrink:0}
.step-detail{margin-top:6px;padding-top:6px;border-top:1px dashed var(--border);font-size:12px;color:var(--text-secondary)}
.sub-steps{margin-left:20px;padding-left:12px;border-left:2px solid var(--border);margin-top:6px}
.att-list{padding-left:16px;margin-top:4px;display:flex;flex-direction:column;gap:4px}
.att-inline{border:1px solid var(--border);border-radius:6px;overflow:hidden;margin-bottom:4px}
.att-label{display:flex;align-items:center;gap:4px;padding:5px 10px;font-size:11px;font-weight:600;color:var(--text-muted);background:#fafafa;border-bottom:1px solid var(--border);text-transform:uppercase;letter-spacing:.3px}
.att-label svg{width:11px;height:11px;stroke:var(--text-muted)}
.att-content{margin:0;padding:6px 10px;font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-all;font-family:monospace;color:var(--text);max-height:300px;overflow:auto}
.att-json .j-key{color:#005cc5}.att-json .j-str{color:#032f62}.att-json .j-num{color:#df5000}.att-json .j-bool{color:#d73a49}.att-json .j-null{color:#999}
.att-img{display:block;max-width:100%;padding:6px}
.tc-labels{display:flex;flex-wrap:wrap;gap:4px}
.label-tag{background:#f6f5f3;padding:2px 6px;border-radius:3px;font-size:11px;color:var(--text-secondary)}
.empty{display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:15px}
"""


_JS = r"""
(async function(){
var b64=__B64__,raw=atob(b64),bytes=new Uint8Array(raw.length);
for(var i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
var ds=new DecompressionStream('gzip'),w=ds.writable.getWriter();w.write(bytes);w.close();
var reader=ds.readable.getReader(),chunks=[],total=0;
while(true){var r=await reader.read();if(r.done)break;chunks.push(r.value);total+=r.value.length}
var merged=new Uint8Array(total),off=0;chunks.forEach(function(c){merged.set(c,off);off+=c.length});
var D=JSON.parse(new TextDecoder().decode(merged));
var P=function(k){try{return JSON.parse(D[k]||'{}')}catch(e){return{}}};
var PA=function(k){try{return JSON.parse(D[k]||'[]')}catch(e){return[]}};
var summary=P('widgets/summary.json'),suitesTree=P('data/suites.json'),behaviorsTree=P('data/behaviors.json'),categoriesTree=P('data/categories.json'),envData=PA('widgets/environment.json'),durationItems=PA('widgets/duration.json');
var curTab='overview',filters={passed:1,failed:1,broken:1,skipped:1,unknown:1},query='';
var sortMode='order',sortDir=1;
var stPrio={failed:0,broken:1,unknown:2,skipped:3,passed:4};
var expandedNodes={},selectedSt={};
function $(s,p){return(p||document).querySelector(s)}
function $$(s,p){return(p||document).querySelectorAll(s)}
function E(t,c,h){var e=document.createElement(t);if(c)e.className=c;if(h!==undefined)e.innerHTML=h;return e}
function fmtDur(ms){if(ms==null||ms<0)return'';if(ms<1000)return ms+'ms';if(ms<60000)return(ms/1000).toFixed(1)+'s';return Math.floor(ms/60000)+'m '+Math.floor((ms%60000)/1000)+'s'}
function sColor(s){return{passed:'#97cc64',failed:'#fd5a3e',broken:'#ffd050',skipped:'#aaa',unknown:'#d35ebe'}[s]||'#d35ebe'}
var IC={clip:'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'};

/* Tree helpers */
function countSt(n,s){var c=0;(function w(x){if(x.status===s)c++;if(x.children)x.children.forEach(w)})(n);return c}
function treeStat(n){var o={};['passed','failed','broken','skipped','unknown'].forEach(function(s){var c=countSt(n,s);if(c)o[s]=c});o.total=0;for(var k in o)if(k!=='total'&&typeof o[k]==='number')o.total+=o[k];return o}
function matchQ(n){if(!query)return 1;if(n.name&&n.name.toLowerCase().indexOf(query)>=0)return 1;if(n.children)return n.children.some(matchQ);return 0}
function getStPrio(n){if(n.status)return stPrio[n.status]!=null?stPrio[n.status]:4;if(countSt(n,'failed'))return 0;if(countSt(n,'broken'))return 1;return 4}
function getOrder(n){if(n.order)return n.order;if(n.children&&n.children.length){var mn=9999;n.children.forEach(function(c){var o=getOrder(c);if(o<mn)mn=o});return mn}return 9999}
function sortNodes(nodes){if(!nodes)return nodes;var copy=nodes.slice();copy.sort(function(a,b){var v=0;if(sortMode==='order'){v=getOrder(a)-getOrder(b)}else if(sortMode==='name')v=(a.name||'').localeCompare(b.name||'');else if(sortMode==='status'){v=getStPrio(a)-getStPrio(b)}else if(sortMode==='duration'){v=(b.time?b.time.duration||0:0)-(a.time?a.time.duration||0:0)}return v*sortDir});return copy}
function expandAll(node){if(node.children&&node.children.length){var nid=node.uid||node.name;if(nid)expandedNodes[nid]=true;node.children.forEach(function(c){expandAll(c)})}}
function collapseAll(){expandedNodes={}}

/* Build tree */
function hasVisible(node){if(node.status)return!!filters[node.status]&&matchQ(node);if(node.children)return node.children.some(hasVisible);return false}
function buildTree(parent,tree,depth){
  if(!tree.children||!tree.children.length)return;
  var ul=E('ul');var sorted=sortNodes(tree.children);
  sorted.forEach(function(node){
    var isLeaf=!!node.status,hasKids=node.children&&node.children.length&&!isLeaf;
    if(isLeaf&&!filters[node.status])return;if(!matchQ(node))return;
    if(hasKids&&!hasVisible(node))return;
    var li=E('li');
    var stClass=isLeaf&&(node.status==='failed'||node.status==='broken')?' st-'+node.status:'';
    var row=E('div','tree-row'+stClass+(hasKids?' group':' leaf'));
    var tog=E('span','tree-toggle');if(hasKids)tog.textContent='\u25B8';row.appendChild(tog);
    if(isLeaf){row.appendChild(E('span','tree-num',''+(node.order||'')))}
    row.appendChild(E('span','tree-icon '+(node.status||'')));
    var nm=E('span','tree-name');nm.textContent=node.name||'';row.appendChild(nm);
    if(hasKids){var ns=treeStat(node);var mini=E('span','tree-mini');var bar=E('span','tree-mini-bar');['passed','failed','broken','skipped','unknown'].forEach(function(s){if(ns[s]){var seg=E('span');seg.style.cssText='flex:'+ns[s]+';background:'+sColor(s);bar.appendChild(seg)}});mini.appendChild(bar);mini.appendChild(E('span','tree-mini-count',(ns.passed||0)+'/'+ns.total));row.appendChild(mini)}
    if(isLeaf&&node.time&&node.time.duration)row.appendChild(E('span','tree-dur',fmtDur(node.time.duration)));
    li.appendChild(row);
    if(isLeaf&&node.uid){row.onclick=function(){$$('.tree-row.active').forEach(function(r){r.classList.remove('active')});row.classList.add('active');showTC(node.uid)}}
    else if(hasKids){var nid=node.uid||node.name;var isOpen=!!expandedNodes[nid];var ch=E('div','tree-children'+(isOpen?'':' collapsed'));ch.setAttribute('data-depth',depth+1);if(isOpen)tog.textContent='\u25BE';buildTree(ch,node,depth+1);li.appendChild(ch);row.onclick=function(){var c=ch.classList.contains('collapsed');ch.classList.toggle('collapsed');tog.textContent=c?'\u25BE':'\u25B8';expandedNodes[nid]=c}}
    ul.appendChild(li);
  });parent.appendChild(ul);
}

/* Render sidebar */
var curTree=null;
var navIcons={
  overview:'<svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  categories:'<svg viewBox="0 0 24 24"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
  suites:'<svg viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
  behaviors:'<svg viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
};

function renderNav(){
  var nc=$('#side-nav-col');nc.innerHTML='';
  var nav=E('div','side-nav');
  // logo
  var logo=E('div','side-nav-logo');
  logo.textContent=summary.reportName||'API Test Report';
  nav.appendChild(logo);
  [{t:'overview',l:'\u603B\u89C8'},{t:'categories',l:'\u7C7B\u522B'},{t:'suites',l:'\u5957\u4EF6'},{t:'behaviors',l:'\u529F\u80FD'}].forEach(function(item){
    var a=E('div','side-nav-item'+(curTab===item.t?' active':''));
    a.innerHTML=(navIcons[item.t]||'')+item.l;
    a.onclick=function(){curTab=item.t;render()};nav.appendChild(a);
  });
  var footer=E('div','side-nav-footer','Standalone HTML Report');
  nav.appendChild(footer);
  nc.appendChild(nav);
}

function renderSidebar(){
  var sb=$('#sidebar');sb.innerHTML='';
  renderNav();
  if(curTab==='overview'){sb.classList.add('hidden');$('#resizer').classList.add('hidden');renderOverview();return}
  sb.classList.remove('hidden');$('#resizer').classList.remove('hidden');
  var trees={suites:suitesTree,behaviors:behaviorsTree,categories:categoriesTree};
  curTree=trees[curTab];
  if(!curTree||!curTree.children||!curTree.children.length){$('#content').innerHTML='<div class="empty">\u65E0\u6570\u636E</div>';return}
  // controls: marks + sorter
  var ctrl=E('div','tree-ctrl');
  var marks=E('div','tree-marks');
  var allSt=['passed','failed','broken','skipped','unknown'];
  var markEls={};
  function updateMarks(){
    var any=Object.keys(selectedSt).length>0;
    allSt.forEach(function(k){
      filters[k]=any?(selectedSt[k]?1:0):1;
      if(markEls[k])markEls[k].className='mark '+(filters[k]?'on':'off')+' '+k;
    });
  }
  allSt.forEach(function(s){
    var c=countSt(curTree,s);if(!c)return;
    var any0=Object.keys(selectedSt).length>0;
    var m=E('span','mark '+((any0&&!selectedSt[s])?'off':'on')+' '+s);m.textContent=c;
    m.onclick=function(e){
      e.stopPropagation();
      if(selectedSt[s]){delete selectedSt[s]}else{selectedSt[s]=1}
      updateMarks();refreshTree();
    };
    markEls[s]=m;marks.appendChild(m);
  });
  ctrl.appendChild(marks);ctrl.appendChild(E('span','tree-strut'));
  var sorter=E('div','tree-sorter');
  [{m:'order',l:'\u987A\u5E8F'},{m:'name',l:'A-Z'},{m:'status',l:'\u72B6\u6001'},{m:'duration',l:'\u65F6\u95F4'}].forEach(function(s){
    var item=E('span','sort-item'+(sortMode===s.m?(sortDir===1?' asc':' desc'):''));
    item.innerHTML='<span class="sort-arrows"><span class="arr-up">\u25B2</span><span class="arr-down">\u25BC</span></span>'+s.l;
    item.onclick=function(e){e.stopPropagation();if(sortMode===s.m){sortDir*=-1}else{sortMode=s.m;sortDir=1}$$('.sort-item').forEach(function(x){x.className='sort-item'});item.className='sort-item'+(sortDir===1?' asc':' desc');refreshTree()};
    sorter.appendChild(item);
  });
  ctrl.appendChild(sorter);
  var expBtns=E('div','tree-expand-btns');
  var btnExpand=E('button');btnExpand.textContent='\u5168\u5C55\u5F00';
  btnExpand.onclick=function(e){e.stopPropagation();expandAll(curTree);refreshTree()};
  var btnCollapse=E('button');btnCollapse.textContent='\u5168\u6298\u53E0';
  btnCollapse.onclick=function(e){e.stopPropagation();collapseAll();refreshTree()};
  expBtns.appendChild(btnExpand);expBtns.appendChild(btnCollapse);
  ctrl.appendChild(expBtns);sb.appendChild(ctrl);
  // search
  var ps=E('div','tree-search');var inp=E('input');inp.placeholder='\u641C\u7D22\u7528\u4F8B...';
  inp.oninput=function(){query=inp.value.toLowerCase();refreshTree()};ps.appendChild(inp);sb.appendChild(ps);
  // tree
  var body=E('div','tree-body');body.id='tree-body';sb.appendChild(body);
  refreshTree();
  $('#content').innerHTML='<div class="empty">\u9009\u62E9\u4E00\u4E2A\u7528\u4F8B\u67E5\u770B\u8BE6\u60C5</div>';
}
function refreshTree(){var b=$('#tree-body');if(!b||!curTree)return;b.innerHTML='';buildTree(b,curTree,0)}

/* Test case detail */
function showTC(uid){
  var k='data/test-cases/'+uid+'.json';if(!D[k]){$('#content').innerHTML='<div class="empty">\u672A\u627E\u5230\u6570\u636E</div>';return}
  var tc=JSON.parse(D[k]),ct=$('#content');ct.innerHTML='';
  var wrap=E('div','tc-wrap');
  wrap.appendChild(E('div','tc-header','<span class="badge '+tc.status+'">'+esc(tc.status)+'</span> <span class="tc-title">'+esc(tc.name)+'</span>'));
  var meta=fmtDur(tc.time?tc.time.duration:0);if(tc.fullName)meta+='  \u00B7  '+esc(tc.fullName);
  wrap.appendChild(E('div','tc-meta',meta));
  if(tc.statusMessage){var sdSec=E('div','tc-section');var sd=E('div','status-details s-'+(tc.status||'failed'));sd.innerHTML='<pre style="margin:0;white-space:pre-wrap;font-size:12px">'+esc(tc.statusMessage)+'</pre>';if(tc.statusTrace){var dt=E('details','tc-trace');dt.innerHTML='<summary>\u5C55\u5F00\u5806\u6808</summary><pre>'+esc(tc.statusTrace)+'</pre>';sd.appendChild(dt)}sdSec.appendChild(sd);wrap.appendChild(sdSec)}
  if(tc.description){var ds=E('div','tc-section');ds.appendChild(E('div','tc-section-title','\u63CF\u8FF0'));ds.appendChild(E('div','',esc(tc.description)));wrap.appendChild(ds)}
  if(tc.parameters&&tc.parameters.length){var ps=E('div','tc-section');ps.appendChild(E('div','tc-section-title','\u53C2\u6570'));var t=E('table','env-table');t.innerHTML='<tr><th>\u540D\u79F0</th><th>\u503C</th></tr>';tc.parameters.forEach(function(p){t.innerHTML+='<tr><td>'+esc(p.name)+'</td><td style="font-family:monospace">'+esc(p.value)+'</td></tr>'});ps.appendChild(t);wrap.appendChild(ps)}
  function stages(title,arr){if(!arr||!arr.length)return;var s=E('div','tc-section');s.appendChild(E('div','tc-section-title',title));arr.forEach(function(st){renderStep(s,st)});wrap.appendChild(s)}
  stages('\u524D\u7F6E',tc.beforeStages);
  if(tc.testStage){var ts=E('div','tc-section');ts.appendChild(E('div','tc-section-title','\u6D4B\u8BD5\u6B65\u9AA4'));if(tc.testStage.steps&&tc.testStage.steps.length)tc.testStage.steps.forEach(function(st){renderStep(ts,st)});if(tc.testStage.attachments&&tc.testStage.attachments.length){var ad=E('div','att-list');tc.testStage.attachments.forEach(function(a){ad.appendChild(mkAtt(a))});ts.appendChild(ad)}wrap.appendChild(ts)}
  if(tc.testStage&&tc.testStage.logAttachments&&tc.testStage.logAttachments.length){var ls=E('div','tc-section');var isFailed=tc.status==='failed'||tc.status==='broken';var det=E('details');if(isFailed)det.setAttribute('open','');det.appendChild(E('summary','tc-section-title','\u65E5\u5FD7 ('+tc.testStage.logAttachments.length+')'));tc.testStage.logAttachments.forEach(function(a){det.appendChild(mkAtt(a))});ls.appendChild(det);wrap.appendChild(ls)}
  stages('\u540E\u7F6E',tc.afterStages);
  if(tc.labels&&tc.labels.length){var ls=E('div','tc-section');ls.appendChild(E('div','tc-section-title','\u6807\u7B7E'));var ld=E('div','tc-labels');tc.labels.forEach(function(l){ld.appendChild(E('span','label-tag',esc(l.name)+': '+esc(l.value)))});ls.appendChild(ld);wrap.appendChild(ls)}
  ct.appendChild(wrap);
}

function renderStep(parent,step){
  var div=E('div','step');
  var st=step.status||'passed';
  var hdr=E('div','step-hdr');
  var badge=E('span','step-badge');badge.style.background=sColor(st);badge.textContent=st;hdr.appendChild(badge);
  hdr.appendChild(E('span','step-name',esc(step.name)));
  if(step.time&&step.time.duration)hdr.appendChild(E('span','step-dur',fmtDur(step.time.duration)));
  div.appendChild(hdr);
  var hasDetail=step.statusMessage||step.statusTrace||(step.time&&step.time.duration);
  if(hasDetail){var detail=E('div','step-detail');
    if(step.time&&step.time.duration){detail.appendChild(E('div','','\u2022 \u8017\u65F6: '+fmtDur(step.time.duration)))}
    if(step.statusMessage){var sd=E('div','status-details s-'+st);sd.style.marginTop='6px';sd.innerHTML='<pre style="margin:0;white-space:pre-wrap;font-size:12px">'+esc(step.statusMessage)+'</pre>';detail.appendChild(sd)}
    if(step.statusTrace){var dt=E('details','tc-trace');dt.setAttribute('open','');dt.innerHTML='<summary>\u5806\u6808\u8DDF\u8E2A</summary><pre>'+esc(step.statusTrace)+'</pre>';detail.appendChild(dt)}
    div.appendChild(detail)}
  if(step.attachments&&step.attachments.length){var ad=E('div','att-list');step.attachments.forEach(function(a){ad.appendChild(mkAtt(a))});div.appendChild(ad)}
  if(step.steps&&step.steps.length){var sd=E('div','sub-steps');step.steps.forEach(function(s){renderStep(sd,s)});div.appendChild(sd)}
  parent.appendChild(div);
}

function mkAtt(att){
  var key='data/attachments/'+att.source,content=D[key]||'',wrap=E('div','att-inline');
  var isLog=att.name&&(att.name.indexOf('log')>=0||att.name.indexOf('Log')>=0||att.name.indexOf('standard')>=0||att.name.indexOf('stdout')>=0||att.name.indexOf('stderr')>=0);
  wrap.appendChild(E('div','att-label',IC.clip+' '+esc(att.name||att.source)));
  if(att.type&&att.type.indexOf('image/')===0){var img=E('img','att-img');img.src=content;wrap.appendChild(img)}
  else{var isJ=att.type==='application/json',text=content;if(isJ){try{text=JSON.stringify(JSON.parse(content),null,2)}catch(e){}}var pre=E('pre','att-content');if(isLog){pre.style.cssText='max-height:600px;overflow:auto;font-size:13px;line-height:1.5;padding:12px;background:#1e1e1e;color:#d4d4d4;border-radius:6px;white-space:pre-wrap;word-wrap:break-word'}if(isJ){pre.classList.add('att-json');pre.innerHTML=syntaxHL(text)}else{pre.textContent=text}wrap.appendChild(pre)}
  return wrap;
}
function syntaxHL(s){return esc(s).replace(/"([^"]+)"(\s*:)/g,'<span class="j-key">"$1"</span>$2').replace(/:\s*"([^"]*)"/g,': <span class="j-str">"$1"</span>').replace(/:\s*(\d+\.?\d*)/g,': <span class="j-num">$1</span>').replace(/:\s*(true|false)/g,': <span class="j-bool">$1</span>').replace(/:\s*null/g,': <span class="j-null">null</span>')}
function esc(s){return s?s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):''}

/* Overview */
function renderOverview(){
  var ct=$('#content');ct.innerHTML='';
  var st=summary.statistic||{},total=st.total||0,passed=st.passed||0,failed=st.failed||0,broken=st.broken||0;
  var ov=E('div','overview');
  ov.appendChild(E('div','ov-title',esc(summary.reportName||'API Test Report')));
  var sub=total+' \u4E2A\u7528\u4F8B';if(summary.time&&summary.time.duration)sub+=' \u00B7 '+fmtDur(summary.time.duration);
  ov.appendChild(E('div','ov-sub',sub));
  var grid=E('div','widgets-grid'),col1=E('div','widgets-col'),col2=E('div','widgets-col');
  // pie chart
  var sw=E('div','widget');sw.appendChild(E('div','widget-title','\u7EDF\u8BA1'));
  var sf=E('div','summary-flex');
  var sz=160,cx=80,cy=80,R=70,ri=46;var svg='<svg width="'+sz+'" height="'+sz+'" viewBox="0 0 '+sz+' '+sz+'">';
  var dd=[{s:'passed',c:passed},{s:'failed',c:failed},{s:'broken',c:broken},{s:'skipped',c:st.skipped||0},{s:'unknown',c:st.unknown||0}].filter(function(d){return d.c>0});
  if(!dd.length)svg+='<circle cx="'+cx+'" cy="'+cy+'" r="'+R+'" fill="#e5e5e5"/>';
  else if(dd.length===1)svg+='<circle cx="'+cx+'" cy="'+cy+'" r="'+R+'" fill="'+sColor(dd[0].s)+'"/><circle cx="'+cx+'" cy="'+cy+'" r="'+ri+'" fill="#fff"/>';
  else{var ag=-90;dd.forEach(function(d){var sw2=d.c/(total||1)*360,s1=ag*Math.PI/180,s2=(ag+sw2)*Math.PI/180,lg=sw2>180?1:0;svg+='<path d="M'+(cx+R*Math.cos(s1))+','+(cy+R*Math.sin(s1))+' A'+R+','+R+' 0 '+lg+',1 '+(cx+R*Math.cos(s2))+','+(cy+R*Math.sin(s2))+' L'+(cx+ri*Math.cos(s2))+','+(cy+ri*Math.sin(s2))+' A'+ri+','+ri+' 0 '+lg+',0 '+(cx+ri*Math.cos(s1))+','+(cy+ri*Math.sin(s1))+' Z" fill="'+sColor(d.s)+'"/>';ag+=sw2})}
  svg+='<text x="'+cx+'" y="'+(cy+5)+'" text-anchor="middle" font-size="28" font-weight="bold">'+total+'</text></svg>';
  sf.innerHTML='<div class="summary-chart">'+svg+'</div>';
  var stats=E('div','summary-stats');
  [{s:'passed',l:'\u901A\u8FC7'},{s:'failed',l:'\u5931\u8D25'},{s:'broken',l:'\u5F02\u5E38'},{s:'skipped',l:'\u8DF3\u8FC7'},{s:'unknown',l:'\u672A\u77E5'}].forEach(function(i){var c=st[i.s]||0;if(!c)return;stats.appendChild(E('div','stat-row','<span class="stat-icon" style="background:'+sColor(i.s)+'"></span><span class="stat-count">'+c+'</span> '+i.l))});
  sf.appendChild(stats);sw.appendChild(sf);col1.appendChild(sw);
  // suites
  var suitesWidget=P('widgets/suites.json');
  if(suitesWidget.items&&suitesWidget.items.length){var su=E('div','widget');su.appendChild(E('div','widget-title','\u5957\u4EF6'));suitesWidget.items.forEach(function(item){var r=E('div','suite-row');r.appendChild(E('span','suite-name',esc(item.name)));var bar=E('div','suite-bar');var ist=item.statistic||{},tot=ist.total||1;['passed','failed','broken','skipped','unknown'].forEach(function(s){if(ist[s]){var seg=E('div');seg.style.cssText='flex:'+ist[s]+';background:'+sColor(s);bar.appendChild(seg)}});r.appendChild(bar);r.appendChild(E('span','suite-count',''+ist.total));su.appendChild(r)});col1.appendChild(su)}
  // duration
  if(durationItems&&durationItems.length){var dw=E('div','widget');dw.appendChild(E('div','widget-title','\u8017\u65F6'));var maxD=Math.max.apply(null,durationItems.map(function(i){return i.time?i.time.duration||0:0}))||1;durationItems.slice(0,20).forEach(function(item){var dur=item.time?item.time.duration||0:0;dw.appendChild(E('div','dur-row','<span class="dur-name">'+esc(item.name)+'</span><div class="dur-bar-wrap"><div class="dur-bar" style="width:'+Math.max(2,dur/maxD*100)+'%;background:'+sColor(item.status)+'"></div></div><span class="dur-val">'+fmtDur(dur)+'</span>'))});col2.appendChild(dw)}
  // env
  if(envData&&envData.length){var ew=E('div','widget');ew.appendChild(E('div','widget-title','\u73AF\u5883'));var tbl=E('table','env-table');tbl.innerHTML='<tr><th>\u540D\u79F0</th><th>\u503C</th></tr>';envData.forEach(function(e){tbl.innerHTML+='<tr><td>'+esc(e.name)+'</td><td>'+esc((e.values||[]).join(', '))+'</td></tr>'});ew.appendChild(tbl);col2.appendChild(ew)}
  grid.appendChild(col1);grid.appendChild(col2);ov.appendChild(grid);ct.appendChild(ov);
}

/* Render */
function render(){
  query='';filters={passed:1,failed:1,broken:1,skipped:1,unknown:1};sortMode='order';sortDir=1;selectedSt={};
  renderSidebar();
}

function initResizer(){var rs=$('#resizer'),sb=$('#sidebar'),sx,sw;rs.addEventListener('mousedown',function(e){sx=e.clientX;sw=sb.offsetWidth;document.addEventListener('mousemove',mv);document.addEventListener('mouseup',up);e.preventDefault()});function mv(e){sb.style.width=Math.max(200,Math.min(600,sw+e.clientX-sx))+'px'}function up(){document.removeEventListener('mousemove',mv);document.removeEventListener('mouseup',up)}}
initResizer();render();
})();
"""



def _build_html(compressed_b64, title):
    css = _CSS
    js = _JS
    safe_title = _html.escape(title)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>\U0001f4ca</text></svg>">
<style>{css}</style>
</head>
<body>
<div class="header">
  <span class="brand">
    <span class="brand-name">{safe_title}</span>
    <span class="brand-dot">\u00B7</span>
    <span class="brand-project"></span>
  </span>
</div>
<div class="main">
  <div class="side-nav-col" id="side-nav-col"></div>
  <div class="sidebar hidden" id="sidebar"></div>
  <div class="resizer hidden" id="resizer"></div>
  <div class="content" id="content"></div>
</div>
<script>var __B64__="{compressed_b64}";</script>
<script>{js}</script>
</body>
</html>'''


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="\u751F\u6210\u6D4B\u8BD5\u62A5\u544A")
    parser.add_argument("--input", default="allure-results", help="allure-results \u76EE\u5F55")
    parser.add_argument("--output", default="allure-report/report.html", help="\u8F93\u51FA HTML")
    parser.add_argument("--title", default=None, help="\u62A5\u544A\u6807\u9898\uff08\u9ED8\u8BA4\u8BFB\u53D6 REPORT_TITLE \u6216\u9879\u76EE\u76EE\u5F55\u540D\uff09")
    parser.add_argument("--clean", action="store_true", help="\u751F\u6210\u524D\u6E05\u7406\u65E7\u62A5\u544A\u76EE\u5F55")
    args = parser.parse_args()
    generate_report(args.input, args.output, title=args.title, clean=args.clean)
