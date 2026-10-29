# Cloudflare challenge 체크박스 자동 클릭

headless 엔진이 Cloudflare challenge 화면에서 기다리는 동안 Turnstile 체크박스를 찾아 클릭한다.
설계 원본은 `~/workspace4/crawler/DESIGN.md` §14(Rust 포팅)이다. 이 문서는 대상 사이트나 엔진이
바뀔 때 무엇을 확인하고 어디를 고칠지 정리한다.

## 1. 동작

- 일반 페이지에서는 클릭하지 않는다. challenge 대기 중에만 동작한다.
- 대기 상한은 90초다. 10초마다 Turnstile 위젯을 찾고, 대기 1회당 최대 3회 클릭한다.
- 위젯 판정: iframe URL이 `https://challenges.cloudflare.com/cdn-cgi/challenge-platform/...`이어야 한다.
  host가 정확히 일치해야 하므로 `challenges.cloudflare.com.evil.test` 같은 외부 iframe은 제외한다.
- 위젯 크기: 폭 200~400px, 높이 40~100px만 인정한다. 클릭 좌표는 `(x + 20, y + height / 2)`다.
  고정 화면 좌표가 아니라 현재 iframe box를 따른다.
- 클릭 중 오류는 시도 횟수에 넣고 대기를 계속한다. 이미지·문자 문제는 풀지 않는다.
- 90초 안에 통과하지 못하면 `make_request`는 `""`를 반환한다. 저장된 쿠키를 버리고 세션을 정리한다.
  `crawler.run()`의 `num_retries`가 새 세션으로 다시 시도한다.
- 통과하면 기존 경로가 `cf_clearance` 쿠키를 엔진별 jar에 저장한다. 다음 요청은 클릭 없이 통과할 수 있다.

## 2. 코드 위치

| 엔진                                                     | 대기 함수                                                                                | 클릭 함수                                                                                                                                              |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| cloakbrowser, camoufox, patchright, rebrowser_playwright | `HeadlessBrowserBase._wait_for_cloudflare` (`bin/headless_browser.py`)                   | `_try_click_cloudflare_checkbox` — Playwright `page.frames` + `frame_element().bounding_box()` + `page.mouse.click`                                    |
| nodriver                                                 | `HeadlessBrowserNodriver._wait_for_cloudflare_html` (`bin/headless_browser_nodriver.py`) | `_try_click_cloudflare_checkbox_cdp` — CDP `DOM.getDocument(pierce=True)`로 closed shadow root까지 탐색, `DOM.getBoxModel`, `Input.dispatchMouseEvent` |
| flaresolverr                                             | 해당 없음                                                                                | FlareSolverr 서버가 직접 처리한다                                                                                                                      |

공통 정책은 `HeadlessBrowserBase`에 있다.

- 상수: `_CLOUDFLARE_CHALLENGE_TIMEOUT_SEC`(90), `_CLOUDFLARE_CLICK_INTERVAL_SEC`(10), `_CLOUDFLARE_MAX_CLICKS`(3)
- 위젯 판정: `_is_cloudflare_challenge_frame(url)`
- 좌표 계산: `_cloudflare_checkbox_point(x, y, width, height)`
- 통과 판정(Playwright): `_CLOUDFLARE_CLEARED_PREDICATE`
- 통과 판정(nodriver·facade): `HeadlessBrowser._contains_cloudflare_challenge(html)`

challenge 대기는 `make_request`의 referer 방문, 본 페이지 방문, `login`의 로그인 페이지 방문에서 호출한다.

## 3. 대상이 바뀔 때 확인할 것

- **Cloudflare가 iframe 경로나 host를 바꿨다**: `_is_cloudflare_challenge_frame`을 고친다.
  `_CLOUDFLARE_CLEARED_PREDICATE`와 `_contains_cloudflare_challenge`의 marker도 함께 맞춘다.
- **위젯 크기나 체크박스 위치가 바뀌었다**: `_cloudflare_checkbox_point`의 크기 범위와 `+20` 오프셋을 고친다.
  실제 화면의 iframe box를 먼저 측정한다. 범위를 넓히면 광고 iframe 오클릭 위험이 커진다.
- **새 Playwright 계열 엔진을 추가한다**: `HeadlessBrowserBase`를 상속하고 `make_request`·`login`을
  `super()`로 위임하면 자동으로 적용된다.
- **Playwright가 아닌 엔진을 추가한다**: nodriver처럼 별도 대기 루프가 필요하다.
  간격·횟수·좌표 정책은 base의 상수와 static method를 재사용한다.
- **사이트가 체크박스 없이 계속 막는다**: 클릭으로 풀리지 않는 판정이다. 엔진 fallback 순서
  (`FM_HEADLESS_BACKEND`, `browser_fallback`)나 브라우저 지문을 검토한다. crawler DESIGN §12 검증·§13에 실패 기록이 있다.
- **사이트 HTML이 challenge marker를 정상 페이지에 포함한다**: 통과 판정이 계속 false가 되어 90초씩 기다린다.
  marker 목록을 좁힌다.

## 4. 테스트

```bash
uv run pytest -q tests/test_headless_browser_cloakbrowser.py tests/test_headless_browser_extra_engines.py
```

- 실제 브라우저를 띄우지 않는 mock 테스트다. 실사이트 통과는 이 테스트로 검증하지 않는다.
- **OOM 주의**: `page.wait_for_function`을 항상 `PlaywrightTimeoutError`로 실패시키는 mock은 즉시 반환한다.
  그러면 `_wait_for_cloudflare`가 90초 동안 sleep 없이 돌고, mock 호출 기록이 쌓여 메모리가 수 GB까지 늘어난다.
  이런 테스트는 `_wait_for_cloudflare`를 patch하거나, `time.monotonic`을 진행시키거나,
  `_CLOUDFLARE_CHALLENGE_TIMEOUT_SEC`를 0으로 줄인다. 실행할 때는 `ulimit -v 6000000`으로 상한을 건다.
- nodriver CDP 테스트의 node id는 `nodriver.cdp.dom.BackendNodeId`로 감싼다. plain int는 `to_json()`이 없어 실패한다.

## 5. 검증 상태와 한계 (2026-10-29)

- mock 단위 테스트는 통과했다.
- bt4g 실접속(cloakbrowser, 쿠키 없는 새 디렉터리, MemoryMax=3G):
  `https://bt4g.com/search?q=ubuntu`를 자동 클릭 1회로 16초에 통과했다.
  제목 `Download ubuntu Torrents - BT4G`, HTML 69,773 bytes, `/magnet/` 링크 15개를 받았고 `cf_clearance`를 저장했다.
- 같은 디렉터리에서 다시 실행하면 저장 쿠키로 3초에 통과했고 클릭은 0회였다.
- 재현 명령(빈 디렉터리에서 실행):

  ```bash
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 -- \
    env PYTHONPATH=<fm_dev> timeout 240 uv run --project <fm_dev> python <fm_dev>/bin/crawler.py \
    --render-js=true --browser-fallback=cloakbrowser --retry=1 'https://bt4g.com/search?q=ubuntu'
  ```

- camoufox·patchright·rebrowser_playwright·nodriver의 실사이트 자동 클릭, 쿠키 장기 재사용은 미검증이다.
- 쿠키 jar(`cookies.*.json`)는 0600으로 쓴다. 예전 실행이 남긴 0644 파일도 다음 저장 때 0600으로 좁힌다.
  bt4g 실행에서 644 → 600 변경을 확인했다.
- 참고 구현(crawler, Rust)은 cloakbrowser로 bt4g·tokyotosho·1337x를 클릭 1회로 통과했다(2026-10-28).
- camoufox(Firefox)의 Turnstile에서 WebGL context 오류가 보고되었다. 클릭이 동작해도 통과는 보장하지 않는다.
- `tests/test_headless_browser_facade.py::test_installed_engines_are_registered_eagerly`의 cloakbrowser subtest는
  `test_headless_browser_cloakbrowser.py`와 함께 실행하면 실패한다. HEAD에서도 재현되는 기존 순서 의존 문제다.
