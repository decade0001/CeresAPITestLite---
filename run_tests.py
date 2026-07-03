#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_by_path(data, path):
    if path in ("", None):
        return data
    current = data
    for part in str(path).split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def set_context_value(context, name, value):
    context[name] = value


def render_value(value, context):
    if isinstance(value, str):
        result = value
        for key, val in context.items():
            result = result.replace("${" + key + "}", str(val))
        return result
    if isinstance(value, dict):
        return {k: render_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [render_value(v, context) for v in value]
    return value


def build_url(base_url, path, params):
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        connector = "&" if "?" in url else "?"
        url = url + connector + query
    return url


def request(case, base_url, context, timeout):
    method = case.get("method", "GET").upper()
    headers = render_value(case.get("headers", {}), context)
    params = render_value(case.get("params", {}), context)
    body = render_value(case.get("json"), context)
    url = build_url(base_url, render_value(case.get("path", ""), context), params)

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json; charset=utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    status_code = None
    raw_text = ""
    error = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            raw_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        raw_text = exc.read().decode("utf-8", errors="replace")
        error = str(exc)
    except Exception as exc:
        error = str(exc)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    json_body = None
    if raw_text:
        try:
            json_body = json.loads(raw_text)
        except Exception:
            json_body = None

    return {
        "url": url,
        "method": method,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "text": raw_text,
        "json": json_body,
        "error": error,
    }


def check_assertion(assertion, response, context):
    assertion = render_value(assertion, context)
    kind = assertion.get("type")
    try:
        if kind == "status_code":
            return response["status_code"] == assertion.get("equals"), f"status_code == {assertion.get('equals')}"
        if kind == "response_time_less_than":
            return response["elapsed_ms"] < assertion.get("ms"), f"elapsed_ms < {assertion.get('ms')}"
        if kind == "contains":
            return assertion.get("value", "") in response.get("text", ""), f"response contains {assertion.get('value')}"
        if kind == "json_field_exists":
            get_by_path(response["json"], assertion.get("path"))
            return True, f"json field exists: {assertion.get('path')}"
        if kind == "json_field_equals":
            actual = get_by_path(response["json"], assertion.get("path"))
            expected = assertion.get("equals")
            return actual == expected, f"json {assertion.get('path')} == {expected}, actual={actual}"
        if kind == "json_field_not_empty":
            actual = get_by_path(response["json"], assertion.get("path"))
            return actual not in (None, "", [], {}), f"json {assertion.get('path')} is not empty"
        return False, f"unknown assertion type: {kind}"
    except Exception as exc:
        return False, f"{kind} failed: {exc}"


def extract_values(extract_rules, response, context):
    extracted = {}
    if not extract_rules:
        return extracted
    for name, path in extract_rules.items():
        try:
            value = get_by_path(response["json"], path)
            set_context_value(context, name, value)
            extracted[name] = value
        except Exception as exc:
            extracted[name] = f"<extract failed: {exc}>"
    return extracted


def run_suite(case_path, override_base_url=None, report_dir="reports", timeout=8, stop_on_fail=False):
    suite = load_json(case_path)
    base_url = override_base_url or suite.get("base_url", "")
    context = dict(suite.get("variables", {}))
    global_headers = suite.get("global_headers", {})
    results = []

    for index, case in enumerate(suite.get("cases", []), start=1):
        merged = dict(case)
        merged["headers"] = {**global_headers, **case.get("headers", {})}
        result = {
            "index": index,
            "name": case.get("name", f"case-{index}"),
            "passed": False,
            "assertions": [],
            "extracted": {},
        }
        try:
            response = request(merged, base_url, context, timeout)
            result["response"] = response
            result["extracted"] = extract_values(case.get("extract"), response, context)
            assertion_results = []
            for assertion in case.get("assertions", []):
                passed, message = check_assertion(assertion, response, context)
                assertion_results.append({"passed": passed, "message": message})
            result["assertions"] = assertion_results
            result["passed"] = bool(assertion_results) and all(item["passed"] for item in assertion_results)
        except Exception:
            result["response"] = {"error": traceback.format_exc(), "status_code": None, "elapsed_ms": None, "text": ""}
            result["assertions"] = [{"passed": False, "message": "case execution error"}]
        results.append(result)
        if stop_on_fail and not result["passed"]:
            break

    summary = {
        "suite": suite.get("name", Path(case_path).stem),
        "base_url": base_url,
        "total": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    write_reports(summary, report_dir)
    return summary


def write_reports(summary, report_dir):
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = Path(report_dir) / f"api_report_{stamp}.json"
    html_path = Path(report_dir) / f"api_report_{stamp}.html"
    dump_json(json_path, summary)
    html_path.write_text(render_html(summary), encoding="utf-8")
    summary["json_report"] = str(json_path)
    summary["html_report"] = str(html_path)


def render_html(summary):
    rows = []
    for item in summary["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        cls = "pass" if item["passed"] else "fail"
        response = item.get("response", {})
        assertions = "<br>".join(
            ("✅ " if a["passed"] else "❌ ") + html.escape(a["message"]) for a in item.get("assertions", [])
        )
        rows.append(
            "<tr>"
            f"<td>{item['index']}</td>"
            f"<td>{html.escape(item['name'])}</td>"
            f"<td class='{cls}'>{status}</td>"
            f"<td>{html.escape(str(response.get('method', '')))}</td>"
            f"<td>{html.escape(str(response.get('status_code', '')))}</td>"
            f"<td>{html.escape(str(response.get('elapsed_ms', '')))}</td>"
            f"<td>{html.escape(str(response.get('url', '')))}</td>"
            f"<td>{assertions}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(summary['suite'])} - API Test Report</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #6b7280; margin-bottom: 18px; }}
    .cards {{ display: flex; gap: 12px; margin-bottom: 18px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 14px; min-width: 100px; }}
    .num {{ font-size: 24px; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; vertical-align: top; }}
    th {{ background: #f3f4f6; text-align: left; }}
    .pass {{ color: #047857; font-weight: 700; }}
    .fail {{ color: #b91c1c; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{html.escape(summary['suite'])}</h1>
  <div class="meta">Base URL: {html.escape(summary['base_url'])} | Generated at: {summary['generated_at']}</div>
  <div class="cards">
    <div class="card"><div>total</div><div class="num">{summary['total']}</div></div>
    <div class="card"><div>passed</div><div class="num pass">{summary['passed']}</div></div>
    <div class="card"><div>failed</div><div class="num fail">{summary['failed']}</div></div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Case</th><th>Status</th><th>Method</th><th>HTTP</th><th>Time(ms)</th><th>URL</th><th>Assertions</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="CeresAPITestLite - lightweight API test runner")
    parser.add_argument("--case", default="cases/demo_cases.json", help="case json file")
    parser.add_argument("--base-url", default=None, help="override base url")
    parser.add_argument("--report-dir", default="reports", help="report output directory")
    parser.add_argument("--timeout", type=int, default=8, help="request timeout seconds")
    parser.add_argument("--stop-on-fail", action="store_true", help="stop after first failed case")
    args = parser.parse_args()

    summary = run_suite(args.case, args.base_url, args.report_dir, args.timeout, args.stop_on_fail)
    print(f"total={summary['total']} passed={summary['passed']} failed={summary['failed']}")
    print(f"html_report={summary['html_report']}")
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
