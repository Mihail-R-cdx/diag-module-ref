"""Inspect the Huawei endpoint UI without changing the diagnostic application.

Usage:
    python inspect_camera_dom.py https://link.ru admin

The password is read with getpass and is never written to disk.
"""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent


def visible_summary(page):
    return page.locator("input, button, a, [role=button]").evaluate_all(
        """elements => elements
          .filter(e => {
            const s = getComputedStyle(e);
            const r = e.getBoundingClientRect();
            return s.visibility !== 'hidden' && s.display !== 'none'
              && r.width > 0 && r.height > 0;
          })
          .map(e => ({
            tag: e.tagName.toLowerCase(),
            id: e.id,
            className: String(e.className),
            type: e.getAttribute('type'),
            name: e.getAttribute('name'),
            placeholder: e.getAttribute('placeholder'),
            text: (e.innerText || e.value || '').trim().slice(0, 120)
          }))"""
    )


def inspect_media_nodes(page):
    return page.locator(
        "img, video, canvas, object, embed, .local-video-screen-box, #localRemoteControl"
    ).evaluate_all(
        """elements => elements.map(e => {
          const r = e.getBoundingClientRect();
          const s = getComputedStyle(e);
          return {
            tag: e.tagName.toLowerCase(),
            id: e.id,
            className: String(e.className),
            parent: e.parentElement && {
              tag: e.parentElement.tagName.toLowerCase(),
              id: e.parentElement.id,
              className: String(e.parentElement.className)
            },
            rect: {x: r.x, y: r.y, width: r.width, height: r.height},
            display: s.display,
            visibility: s.visibility,
            opacity: s.opacity,
            backgroundImage: s.backgroundImage,
            src: e.currentSrc || e.src || e.data || null
          };
        })"""
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("username")
    parser.add_argument("--password")
    parser.add_argument(
        "--click-text",
        action="append",
        default=[],
        help="Visible text to click after login; may be passed more than once",
    )
    parser.add_argument(
        "--probe-api",
        action="store_true",
        help="Read current camera/video state from safe GET endpoints",
    )
    args = parser.parse_args()
    password = args.password or getpass.getpass("Password: ")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--ignore-certificate-errors"],
        )
        context = browser.new_context(ignore_https_errors=True, viewport={"width": 1600, "height": 1000})
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_000)

        (HERE / "live-before-login.html").write_text(page.content(), encoding="utf-8")
        print("Before login:")
        print(json.dumps(visible_summary(page), ensure_ascii=False, indent=2))

        inputs = page.locator("input:visible")
        password_input = page.locator("input[type=password]:visible")
        if inputs.count() and password_input.count():
            user_input = page.locator(
                "input[type=text]:visible, input:not([type]):visible"
            ).first
            user_input.fill(args.username)
            password_input.first.fill(password)
            submit = page.locator(
                "button[type=submit]:visible, input[type=submit]:visible, button:visible"
            ).first
            submit.click()
            page.wait_for_timeout(4_000)

        for index, text in enumerate(args.click_text, start=1):
            target = page.get_by_text(text, exact=True).first
            target.click()
            page.wait_for_timeout(2_000)
            (HERE / f"live-after-click-{index}.html").write_text(
                page.content(), encoding="utf-8"
            )
            print(f"After click {index} ({text!r}): {page.url}")
            print(json.dumps(visible_summary(page), ensure_ascii=False, indent=2))

        if args.probe_api:
            api_state = page.evaluate(
                """async () => {
                  const urls = [
                    '/v1/login/status',
                    '/v1/mediacontrol/input',
                    '/v1/mediacontrol/video-input/devices',
                    '/v1/mediacontrol/video-output/devices',
                    '/v1/mediacontrol/layout',
                    '/v1/mediacontrol/camera/position?cameraId=0',
                    '/v1/mediacontrol/camera/setting?cameraId=0'
                  ];
                  const result = {};
                  for (const url of urls) {
                    try {
                      const response = await fetch(url, {credentials: 'same-origin'});
                      result[url] = {
                        status: response.status,
                        body: (await response.text()).slice(0, 12000)
                      };
                    } catch (error) {
                      result[url] = {error: String(error)};
                    }
                  }
                  return result;
                }"""
            )
            print("Read-only API state:")
            print(json.dumps(api_state, ensure_ascii=False, indent=2))

        (HERE / "live-after-login.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=HERE / "live-after-login.png", full_page=True)
        print(f"After login: {page.url}")
        print(json.dumps(visible_summary(page), ensure_ascii=False, indent=2))
        print("Media-like nodes:")
        print(json.dumps(inspect_media_nodes(page), ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
