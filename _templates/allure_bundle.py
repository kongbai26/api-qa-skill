#!/usr/bin/env python3
"""
Allure 报告打包器 v3
===================
把 allure-report/ 打包成单 HTML 文件。
不用 iframe，直接在同一页面内联所有内容 + XHR 拦截。

前提：需要先用 allure generate 生成过 allure-report/
用法：python utils/allure_bundle.py
"""

import os, sys, json, base64
from pathlib import Path


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def read_binary(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except:
        return b""


def write_text_if_changed(path, content):
    """Avoid replacing a byte-identical standalone bundle."""
    output = Path(path)
    try:
        if output.read_text(encoding="utf-8") == content:
            return False
    except OSError:
        pass
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return True


def bundle(report_dir="allure-report", output="allure-report/bundle.html"):
    report = Path(report_dir)
    if not (report / "app.js").exists():
        print(f"错误: {report_dir}/app.js 不存在")
        sys.exit(1)

    print("读取文件...")

    # 收集所有需要通过 XHR 加载的数据文件
    data_files = {}
    for subdir in ["data", "widgets", "data/test-cases", "data/attachments"]:
        d = report / subdir
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    rel = str(f.relative_to(report)).replace("\\", "/")
                    content = read_text(f)
                    if content:
                        data_files[rel] = content

    print(f"  数据文件: {len(data_files)} 个")

    # 读取前端文件
    app_js = read_text(report / "app.js")
    styles_css = read_text(report / "styles.css")
    favicon_bytes = read_binary(report / "favicon.ico")
    favicon_b64 = base64.b64encode(favicon_bytes).decode() if favicon_bytes else ""

    # 插件
    plugins_js = ""
    plugins_css = ""
    plugin_dir = report / "plugin"
    if plugin_dir.exists():
        for p in sorted(plugin_dir.iterdir()):
            if p.is_dir():
                js = p / "index.js"
                css = p / "styles.css"
                if js.exists():
                    plugins_js += read_text(js) + "\n"
                if css.exists():
                    plugins_css += read_text(css) + "\n"

    # 把数据文件 JSON 序列化
    # 关键：必须转义 </script>，否则浏览器会提前关闭 script 标签
    data_json = json.dumps(data_files, ensure_ascii=False, sort_keys=True)
    data_json = data_json.replace("</script>", "<\\/script>")
    data_json = data_json.replace("</Script>", "<\\/Script>")
    data_json = data_json.replace("</SCRIPT>", "<\\/SCRIPT>")

    # 构建 HTML — 关键：XHR 拦截器在 app.js 之前执行
    html = f"""<!DOCTYPE html>
<html dir="ltr" lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>Allure Report</title>
    <link rel="icon" href="data:image/x-icon;base64,{favicon_b64}">
    <style>
{styles_css}
{plugins_css}
    </style>

    <script>
    // ========== XHR 拦截器（必须在 app.js 之前执行）==========
    (function() {{
        var __DATA__ = {data_json};

        var OrigXHR = XMLHttpRequest;

        function FakeXHR() {{
            this._headers = {{}};
            this._method = '';
            this._url = '';
            this._async = true;
            this._realXHR = null;
            this._intercepted = false;
            this.readyState = 0;
            this.status = 0;
            this.statusText = '';
            this.responseText = '';
            this.response = '';
            this.responseType = '';
            this.onreadystatechange = null;
            this.onload = null;
            this.onerror = null;
            this.onprogress = null;
            this.onloadend = null;
        }}

        FakeXHR.prototype.open = function(method, url, async) {{
            this._method = method;
            this._url = url;
            this._async = async !== false;

            // 标准化路径
            var key = url.replace(/^\\.?\\//, '');

            if (__DATA__.hasOwnProperty(key)) {{
                this._intercepted = true;
                this._responseData = __DATA__[key];
            }} else {{
                this._intercepted = false;
                this._realXHR = new OrigXHR();
                var self = this;
                this._realXHR.onreadystatechange = function() {{
                    self.readyState = self._realXHR.readyState;
                    if (self._realXHR.readyState === 4) {{
                        self.status = self._realXHR.status;
                        self.statusText = self._realXHR.statusText;
                        self.responseText = self._realXHR.responseText;
                        self.response = self._realXHR.response;
                    }}
                    if (self.onreadystatechange) self.onreadystatechange();
                }};
                this._realXHR.onload = function() {{ if (self.onload) self.onload(); }};
                this._realXHR.onerror = function() {{ if (self.onerror) self.onerror(); }};
                this._realXHR.open(method, url, async !== false);
            }}
        }};

        FakeXHR.prototype.send = function(body) {{
            if (this._intercepted) {{
                var self = this;
                self.readyState = 4;
                self.status = 200;
                self.statusText = 'OK';
                self.responseText = self._responseData;
                self.response = self._responseData;

                setTimeout(function() {{
                    if (self.onreadystatechange) self.onreadystatechange();
                    if (self.onload) self.onload();
                    if (self.onloadend) self.onloadend();
                }}, 0);
            }} else if (this._realXHR) {{
                this._realXHR.send(body);
            }}
        }};

        FakeXHR.prototype.setRequestHeader = function(k, v) {{
            if (this._realXHR) this._realXHR.setRequestHeader(k, v);
        }};

        FakeXHR.prototype.getResponseHeader = function(k) {{
            if (this._intercepted) {{
                if (k.toLowerCase() === 'content-type') return 'application/json';
                return null;
            }}
            if (this._realXHR) return this._realXHR.getResponseHeader(k);
            return null;
        }};

        FakeXHR.prototype.getAllResponseHeaders = function() {{
            if (this._intercepted) return 'content-type: application/json\\r\\n';
            if (this._realXHR) return this._realXHR.getAllResponseHeaders();
            return '';
        }};

        FakeXHR.prototype.abort = function() {{
            if (this._realXHR) this._realXHR.abort();
        }};

        FakeXHR.prototype.addEventListener = function(type, fn) {{
            if (type === 'load') this.onload = fn;
            else if (type === 'error') this.onerror = fn;
            else if (type === 'readystatechange') this.onreadystatechange = fn;
            else if (type === 'loadend') this.onloadend = fn;
            if (this._realXHR) this._realXHR.addEventListener(type, fn);
        }};

        FakeXHR.prototype.removeEventListener = function() {{}};
        FakeXHR.prototype.overrideMimeType = function() {{}};

        // 替换全局 XMLHttpRequest
        window.XMLHttpRequest = FakeXHR;
    }})();
    </script>
</head>
<body>
    <div id="alert"></div>
    <div id="content">
        <span class="spinner">
            <span class="spinner__circle"></span>
        </span>
    </div>
    <div id="popup"></div>

    <script>
{app_js}
    </script>
    <script>
{plugins_js}
    </script>
</body>
</html>"""

    was_written = write_text_if_changed(output, html)

    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"打包{'完成' if was_written else '内容未变化'}: {output} ({size_mb:.1f}MB)")
    print(f"数据: {len(data_files)} 个文件内联")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="打包 allure-report 为单 HTML")
    parser.add_argument("--input", default="allure-report", help="allure-report 目录")
    parser.add_argument("--output", default="allure-report/bundle.html", help="输出文件")
    args = parser.parse_args()
    bundle(args.input, args.output)
