import argparse
import io
import json
import os
import random
import sys
import tempfile
from pathlib import Path

import requests
import pycurl

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.ssl_adapter import SSLAdapter, create_legacy_ssl_context


def decode_response(response):
    return response.content.decode("utf-8", errors="replace")


def post_action(session, base_url, action_id, payload=None, headers=None):
    url = f"{base_url}/action.cgi?ActionID={action_id}"
    if payload is None:
        response = session.post(url, data="", headers=headers, timeout=15)
    else:
        response = session.post(url, json=payload, headers=headers, timeout=15)
    return url, response


def pycurl_request(url, cookie_jar_path, *, method="POST", data="", headers=None):
    body = io.BytesIO()
    response_headers = io.BytesIO()
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    if method == "POST":
        curl.setopt(pycurl.POST, 1)
        curl.setopt(pycurl.POSTFIELDS, data)
    else:
        curl.setopt(pycurl.HTTPGET, 1)
    curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    curl.setopt(pycurl.CONNECTTIMEOUT, 10)
    curl.setopt(pycurl.TIMEOUT, 30)
    curl.setopt(pycurl.HEADERFUNCTION, response_headers.write)
    curl.setopt(pycurl.WRITEFUNCTION, body.write)
    curl.setopt(pycurl.COOKIEFILE, cookie_jar_path)
    curl.setopt(pycurl.COOKIEJAR, cookie_jar_path)
    curl.setopt(pycurl.FOLLOWLOCATION, 0)
    curl.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1)
    curl.setopt(pycurl.USERAGENT, "TE20Diag/1.0")
    if headers:
        curl.setopt(pycurl.HTTPHEADER, headers)

    try:
        curl.perform()
        return {
            "status": curl.getinfo(pycurl.RESPONSE_CODE),
            "body": body.getvalue().decode("utf-8", errors="replace"),
            "headers": response_headers.getvalue().decode("utf-8", errors="replace"),
        }
    finally:
        curl.close()


def read_session_id_from_cookie_jar(cookie_jar_path):
    try:
        with open(cookie_jar_path, "r", encoding="utf-8", errors="replace") as cookie_file:
            for line in cookie_file:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7 and parts[-2] == "SessionID":
                    return parts[-1]
    except OSError:
        pass
    return ""


def export_with_pycurl(base_url, username, password):
    fd, cookie_jar_path = tempfile.mkstemp(prefix="te20_export_cookie_", suffix=".txt")
    os.close(fd)
    headers = [
        "Accept: */*",
        "X-Requested-With: XMLHttpRequest",
        "userType: web",
        f"Origin: {base_url}",
        f"Referer: {base_url}/login.html",
    ]

    try:
        session_url = f"{base_url}/action.cgi?ActionID=Web_RequestSessionID"
        print(f"[session/pycurl] POST {session_url}")
        session_response = pycurl_request(session_url, cookie_jar_path, headers=headers)
        print(f"[session/pycurl] status={session_response['status']} body={session_response['body'][:500]}")

        token_url = f"{base_url}/action.cgi?ActionID=Web_RequestCertificate"
        token_payload = json.dumps({"user": username, "password": password}, ensure_ascii=False)
        print(f"[auth/pycurl] POST {token_url}")
        token_response = pycurl_request(
            token_url,
            cookie_jar_path,
            data=token_payload,
            headers=headers + ["Content-Type: application/json"],
        )
        print(f"[auth/pycurl] status={token_response['status']} body={token_response['body'][:500]}")

        session_id = read_session_id_from_cookie_jar(cookie_jar_path)
        if session_id:
            print(f"[session/pycurl] cookie SessionID={session_id}")

        rmd = random.random()
        export_url = f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport?rmd={rmd}"
        print(f"[export/pycurl] GET {export_url}")
        export_response = pycurl_request(export_url, cookie_jar_path, method="GET", headers=headers)
        print(f"[export/pycurl] status={export_response['status']} bytes={len(export_response['body'].encode('utf-8'))}")
        print(f"[export/pycurl] preview={export_response['body'][:300]}")
        return export_response["body"]
    finally:
        try:
            os.remove(cookie_jar_path)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Export Huawei TE-20 call log XML.")
    parser.add_argument("--ip", default="192.168.1.100")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="***REMOVED_CREDENTIAL***")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--http", action="store_true", help="Use HTTP:80 instead of HTTPS:443.")
    parser.add_argument("--pycurl", action="store_true", help="Use pycurl/Schannel-style transport for HTTPS.")
    parser.add_argument("--probe", action="store_true", help="Try several HTTP export URL variants.")
    parser.add_argument("--p2p", action="store_true", help="Use WEB_GetP2PCallRecordsAPI instead of XML export.")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    scheme = "http" if args.http else "https"
    port = 80 if args.http else args.port
    base_url = f"{scheme}://{args.ip}:{port}"

    session = requests.Session()
    session.verify = False
    if scheme == "https":
        session.mount("https://", SSLAdapter(ssl_context=create_legacy_ssl_context(verify_ssl=False)))
    requests.packages.urllib3.disable_warnings()

    print(f"[connect] base_url={base_url}")

    if args.pycurl:
        xml_text = export_with_pycurl(base_url, args.username, args.password)
        output_path = Path(args.output) if args.output else Path(__file__).with_name("output") / f"te20_call_log_{args.ip.replace('.', '_')}.xml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(xml_text, encoding="utf-8")
        print(f"[done] saved to {output_path}")
        return

    session_url, session_response = post_action(session, base_url, "WEB_RequestSessionIDAPI")
    session_text = decode_response(session_response)
    print(f"[session] POST {session_url}")
    print(f"[session] status={session_response.status_code} body={session_text[:500]}")
    session_response.raise_for_status()

    session_id = session.cookies.get("SessionID", "")
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["Sessionid"] = session_id
        print(f"[session] cookie SessionID={session_id}")

    token_payload = {"user": args.username, "password": args.password}
    token_url, token_response = post_action(
        session,
        base_url,
        "WEB_RequestCertificateAPI",
        payload=token_payload,
        headers=headers,
    )
    token_text = decode_response(token_response)
    print(f"[auth] POST {token_url}")
    print(f"[auth] status={token_response.status_code} body={token_text[:500]}")
    token_response.raise_for_status()

    csrf_token = ""
    try:
        token_result = json.loads(token_text)
        token_data = token_result.get("data")
        if token_data:
            csrf_token = json.loads(token_data).get("acCSRFToken", "")
    except json.JSONDecodeError:
        pass
    if csrf_token:
        headers["acCSRFToken"] = csrf_token
        print("[auth] CSRF token received")

    rmd = random.random()
    if args.p2p:
        p2p_url = f"{base_url}/action.cgi?ActionID=WEB_GetP2PCallRecordsAPI?rmd={rmd}"
        p2p_payload = {"acCSRFToken": csrf_token}
        print(f"[p2p] POST {p2p_url}")
        p2p_response = session.post(p2p_url, json=p2p_payload, headers=headers, timeout=30)
        p2p_text = decode_response(p2p_response)
        print(f"[p2p] status={p2p_response.status_code} bytes={len(p2p_response.content)}")
        print(f"[p2p] preview={p2p_text[:1000]}")
        p2p_response.raise_for_status()

        output_path = Path(args.output) if args.output else Path(__file__).with_name("output") / f"te20_p2p_call_records_{args.ip.replace('.', '_')}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(p2p_text, encoding="utf-8")
        print(f"[done] saved to {output_path}")
        return

    export_variants = [
        ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport?rmd={rmd}", headers),
        ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport&rmd={rmd}", headers),
        ("POST", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport?rmd={rmd}", headers),
        ("POST", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport&rmd={rmd}", headers),
        ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExportAPI?rmd={rmd}", headers),
        ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExportAPI&rmd={rmd}", headers),
    ]
    if csrf_token:
        csrf_headers = dict(headers)
        csrf_headers["acCSRFToken"] = csrf_token
        csrf_headers["X-CSRF-Token"] = csrf_token
        export_variants.extend([
            ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport?rmd={rmd}&acCSRFToken={csrf_token}", csrf_headers),
            ("GET", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport&rmd={rmd}&acCSRFToken={csrf_token}", csrf_headers),
            ("POST", f"{base_url}/action.cgi?ActionID=WEB_CallRecordExport?rmd={rmd}", csrf_headers),
        ])

    export_response = None
    xml_text = ""
    variants_to_try = export_variants if args.probe else export_variants[:1]
    for method, export_url, export_headers in variants_to_try:
        print(f"[export] {method} {export_url}")
        if method == "POST":
            export_response = session.post(export_url, data="", headers=export_headers, timeout=30)
        else:
            export_response = session.get(export_url, headers=export_headers, timeout=30)
        xml_text = decode_response(export_response)
        print(f"[export] status={export_response.status_code} bytes={len(export_response.content)}")
        print(f"[export] preview={xml_text[:300]}")
        if xml_text.lstrip().startswith("<?xml") or "<CallRecordsModule>" in xml_text:
            break
        if args.probe:
            print("[export] variant did not return XML")

    if export_response is None:
        raise RuntimeError("No export request was sent")
    export_response.raise_for_status()
    if not (xml_text.lstrip().startswith("<?xml") or "<CallRecordsModule>" in xml_text):
        raise RuntimeError(f"Export did not return XML: {xml_text[:300]}")

    output_path = Path(args.output) if args.output else Path(__file__).with_name("output") / f"te20_call_log_{args.ip.replace('.', '_')}.xml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_text, encoding="utf-8")
    print(f"[done] saved to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
