"""Sesiuni autentificate lege5.ro / lege6.ro pe baza de browser (Playwright async).

DE CE BROWSER (rescriere 2026-06-27):
  lege5.ro si lege6.ro sunt aplicatii SPA (randate in client, JavaScript) in spatele
  unui cont Indaco platit. Un client HTTP simplu (httpx) primea:
    - la cautare: scheletul gol al SPA-ului -> 0 rezultate "in tacere";
    - la login lege6: HTTP 400, fiindca formularul real foloseste campurile
      usernameOrEmailAddress/password + token antiforgery, nu Input.Email.
  Solutia corecta este un browser real care executa JavaScript-ul, tine sesiunea
  logata si apeleaza API-ul intern JSON al platformei. Playwright async se
  integreaza nativ in bucla asyncio a serverului MCP (fara thread-uri separate).

Interfata pastrata pentru clienti:
  - await session.ensure_authenticated() -> bool
  - await session.fetch_json(url)        -> dict   (fetch autentificat, in origine)
  - await session.goto_text(url)         -> dict {text,title,html,url}
  - await session.close()
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("legal-verificator.auth")

LEGE5_BASE = "https://lege5.ro"
LEGE5_LOGIN_URL = f"{LEGE5_BASE}/Authentication/Login"
LEGE6_BASE = "https://lege6.ro"
LEGE6_LOGIN_URL = f"{LEGE6_BASE}/account/login"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_STATE_DIR = Path(__file__).resolve().parent.parent.parent / ".session"

# Browser partajat (lansat lazy, o singura data, pe bucla serverului).
_playwright = None
_browser = None
_browser_lock = asyncio.Lock()


async def _get_browser():
    global _playwright, _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(headless=True)
        return _browser


class _IndacoSession:
    """Baza comuna pentru sesiunile lege5/lege6 (Playwright)."""

    site_name = "indaco"
    base = ""
    state_file = "state.json"

    def __init__(self):
        self._context = None
        self._page = None
        self._authenticated = False
        self._lock = asyncio.Lock()
        # Lock separat de _lock: ensure_authenticated apeleaza _ensure_page tinand
        # deja _lock, iar asyncio.Lock nu e reentrant, deci refolosirea lui ar bloca.
        self._page_lock = asyncio.Lock()
        # Navigarile pe pagina partajata se serializeaza intre ele.
        self._nav_lock = asyncio.Lock()

    async def _ensure_page(self):
        # Doua apeluri de tool concurente pe o sesiune proaspata ar vedea amandoua
        # _page = None si ar deschide fiecare cate un context; unul ar ramane orfan,
        # cu Chromium-ul lui cu tot. Verificare dubla, inainte si dupa lock.
        if self._page is not None:
            return self._page
        async with self._page_lock:
            if self._page is not None:
                return self._page
            browser = await _get_browser()
            _STATE_DIR.mkdir(exist_ok=True)
            state_path = _STATE_DIR / self.state_file
            kwargs = dict(locale="ro-RO", user_agent=_USER_AGENT)
            if state_path.exists():
                kwargs["storage_state"] = str(state_path)
            context = await browser.new_context(**kwargs)
            context.set_default_timeout(45000)
            page = await context.new_page()
            self._context = context
            self._page = page
            return self._page

    async def _save_state(self):
        try:
            _STATE_DIR.mkdir(exist_ok=True)
            await self._context.storage_state(path=str(_STATE_DIR / self.state_file))
        except Exception as e:
            logger.debug("%s: could not save state: %s", self.site_name, e)

    # ---- de implementat per-site ----
    async def _do_login(self, page) -> bool:
        raise NotImplementedError

    async def _is_logged_in(self, page) -> bool:
        raise NotImplementedError

    async def ensure_authenticated(self) -> bool:
        if self._authenticated:
            return True
        async with self._lock:
            if self._authenticated:
                return True
            page = await self._ensure_page()
            # Sesiunea persistenta poate fi inca valida.
            try:
                if await self._is_logged_in(page):
                    self._authenticated = True
                    return True
            except Exception:
                pass
            ok = await self._do_login(page)
            if ok:
                self._authenticated = True
                await self._save_state()
            return ok

    async def fetch_json(self, url: str) -> dict:
        """Fetch autentificat din originea site-ului (executat in pagina logata)."""
        page = await self._ensure_page()
        txt = await page.evaluate(
            """async (u) => {
                const r = await fetch(u, {headers: {'Accept': 'application/json'}, credentials: 'include'});
                return await r.text();
            }""",
            url,
        )
        import json
        return json.loads(txt)

    async def post_json(self, url: str, body: dict) -> dict:
        """POST JSON autentificat din originea site-ului (executat in pagina logata)."""
        page = await self._ensure_page()
        txt = await page.evaluate(
            """async ([u, b]) => {
                // Aplicatiile Angular ataseaza X-XSRF-TOKEN din cookie la POST-uri;
                // fara el serverul poate respinge cererea fara mesaj de eroare.
                const m = document.cookie.match(/(?:^|; )XSRF-TOKEN=([^;]+)/);
                const headers = {'Accept': 'application/json', 'Content-Type': 'application/json'};
                if (m) headers['X-XSRF-TOKEN'] = decodeURIComponent(m[1]);
                const r = await fetch(u, {
                    method: 'POST',
                    headers,
                    credentials: 'include',
                    body: JSON.stringify(b),
                });
                return await r.text();
            }""",
            [url, body],
        )
        import json
        # Corp gol = "niciun rezultat" pentru API-urile de cautare (sintact intoarce
        # 200 cu body vid cand nu exista potrivire), nu o eroare de parsare.
        if not (txt or "").strip():
            return {}
        return json.loads(txt)

    async def goto_text(self, url: str) -> dict:
        """Navigheaza la un document si extrage textul randat.

        Serializat: sesiunea are o singura pagina, deci doua navigari concurente
        s-ar calca reciproc si a doua ar returna textul primeia."""
        page = await self._ensure_page()
        async with self._nav_lock:
            return await self._goto_text_locked(page, url)

    async def _goto_text_locked(self, page, url: str) -> dict:
        await page.goto(url, timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        # Vizualizatorul lege6 incarca textul lazy la scroll — deruleaza ca sa il fortezi.
        try:
            for _ in range(6):
                await page.evaluate(
                    """() => { const c = document.querySelector('#tabAfisareAct') || document.scrollingElement || document.body;
                               c.scrollTop = c.scrollHeight; window.scrollTo(0, document.body.scrollHeight); }"""
                )
                await page.wait_for_timeout(700)
        except Exception:
            pass
        title = await page.title()
        text = await page.evaluate(
            """() => {
                const sel = ['#tabAfisareAct', '.continutAct', '#continutAct',
                             '.document-content', '.act-content', 'main', 'article'];
                let best = '';
                for (const s of sel) {
                    const e = document.querySelector(s);
                    if (e && e.innerText && e.innerText.trim().length > best.length) best = e.innerText.trim();
                }
                const body = document.body ? document.body.innerText.trim() : '';
                // Daca containerul dedicat e mult mai mic decat body-ul, foloseste body-ul
                // (textul actului consolidat se afla raspandit in pagina).
                return (best.length >= 800 && best.length >= body.length * 0.5) ? best : (body || best);
            }"""
        )
        return {"text": text or "", "title": title, "url": page.url}

    async def goto_rendered_html(self, url: str, wait_ms: int = 5000) -> str:
        """Navigheaza la o pagina SPA si returneaza HTML-ul DUPA ce ruleaza JavaScript."""
        page = await self._ensure_page()
        async with self._nav_lock:
            await page.goto(url, timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            await page.wait_for_timeout(wait_ms)
            return await page.content()

    async def close(self):
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        self._context = None
        self._page = None
        self._authenticated = False


class Lege6Session(_IndacoSession):
    """lege6.ro — platforma Indaco moderna (ASP.NET Core + SPA)."""

    site_name = "lege6"
    base = LEGE6_BASE
    state_file = "lege6_state.json"

    def __init__(self):
        super().__init__()
        self._email = os.environ.get("LEGE6_EMAIL", "") or os.environ.get("LEGE5_EMAIL", "")
        self._password = os.environ.get("LEGE6_PASSWORD", "") or os.environ.get("LEGE5_PASSWORD", "")

    async def _is_logged_in(self, page) -> bool:
        await page.goto(f"{LEGE6_BASE}/app", timeout=45000)
        await page.wait_for_timeout(1500)
        return "/account/login" not in page.url.lower()

    async def _do_login(self, page) -> bool:
        if not self._email or not self._password:
            logger.warning("Lege6 credentials missing (LEGE6_EMAIL/LEGE6_PASSWORD)")
            return False
        try:
            await page.goto(LEGE6_LOGIN_URL, timeout=60000)
            await page.wait_for_timeout(1200)
            await page.fill('input[name="usernameOrEmailAddress"]', self._email)
            await page.fill('input[name="password"]', self._password)
            try:
                await page.check('input[name="rememberMe"]')
            except Exception:
                pass
            await page.click('#kt_login_signin_submit')
            await page.wait_for_timeout(3500)
            ok = "/account/login" not in page.url.lower()
            if ok:
                logger.info("Lege6.ro login successful")
            else:
                logger.error("Lege6.ro login failed (still on login page)")
            return ok
        except Exception as e:
            logger.error("Lege6.ro login error: %s", e)
            return False


SINTACT_BASE = "https://sintact.ro"


class SintactSession(_IndacoSession):
    """sintact.ro — platforma Wolters Kluwer Romania (legislatie, jurisprudenta, doctrina).

    Login-ul redirectioneaza catre SSO-ul central Wolters Kluwer
    (autentificare.wolterskluwer.ro, aplicatia interna "Andromeda"/"Borg"), care
    intoarce apoi utilizatorul autentificat pe sintact.ro. Cautarea si documentele
    se obtin din API-ul JSON intern (searchResults.get.json, search.direct.hit.get.json,
    act.get.json), verificat live iulie 2026, nu din HTML randat.
    """

    site_name = "sintact"
    base = SINTACT_BASE
    state_file = "sintact_state.json"

    def __init__(self):
        super().__init__()
        self._email = os.environ.get("SINTACT_EMAIL", "")
        self._password = os.environ.get("SINTACT_PASSWORD", "")

    async def _is_logged_in(self, page) -> bool:
        await page.goto(SINTACT_BASE, timeout=45000)
        await page.wait_for_timeout(1500)
        return "autentificare.wolterskluwer.ro" not in page.url.lower()

    async def _do_login(self, page) -> bool:
        if not self._email or not self._password:
            logger.warning("Sintact credentials missing (SINTACT_EMAIL/SINTACT_PASSWORD)")
            return False
        try:
            await page.goto(SINTACT_BASE, timeout=60000)
            await page.wait_for_timeout(2000)
            # Banner OneTrust de consimtamant cookie-uri, poate bloca formularul dedesubt.
            try:
                await page.click("button:has-text('Accept')", timeout=3000)
            except Exception:
                pass
            await page.fill('input[name="login"]', self._email)
            await page.fill('input[name="password"]', self._password)
            await page.click("#login_btn")
            await page.wait_for_timeout(4000)
            ok = "autentificare.wolterskluwer.ro" not in page.url.lower()
            if ok:
                logger.info("Sintact.ro login successful")
            else:
                logger.error("Sintact.ro login failed (still on WK SSO page)")
            return ok
        except Exception as e:
            logger.error("Sintact.ro login error: %s", e)
            return False


class Lege5Session(_IndacoSession):
    """lege5.ro — platforma Indaco clasica (MVC + SPA pentru cautare)."""

    site_name = "lege5"
    base = LEGE5_BASE
    state_file = "lege5_state.json"

    def __init__(self):
        super().__init__()
        self._email = os.environ.get("LEGE5_EMAIL", "")
        self._password = os.environ.get("LEGE5_PASSWORD", "")

    async def _is_logged_in(self, page) -> bool:
        await page.goto(f"{LEGE5_BASE}/MyLege5", timeout=45000)
        await page.wait_for_timeout(1500)
        return "/authentication/login" not in page.url.lower()

    async def _do_login(self, page) -> bool:
        if not self._email or not self._password:
            logger.warning("Lege5 credentials missing (LEGE5_EMAIL/LEGE5_PASSWORD)")
            return False
        try:
            await page.goto(LEGE5_LOGIN_URL, timeout=60000)
            await page.wait_for_timeout(1200)
            await page.fill('input[name="Login.Mail"]', self._email)
            await page.fill('input[name="Login.Password"]', self._password)
            # Formularul lege5 nu are un button[type=submit] standard — submit cu Enter,
            # cu click pe orice buton de login ca rezerva (timeout scurt).
            try:
                await page.press('input[name="Login.Password"]', "Enter")
            except Exception:
                pass
            await page.wait_for_timeout(1500)
            if "/authentication/login" in page.url.lower():
                try:
                    await page.click('button:has-text("Autentificare"), a:has-text("Autentificare"), .js-loginBtn, #loginButton', timeout=4000)
                except Exception:
                    pass
            await page.wait_for_timeout(3000)
            ok = "/authentication/login" not in page.url.lower()
            if ok:
                logger.info("Lege5.ro login successful")
            else:
                logger.error("Lege5.ro login failed (still on login page)")
            return ok
        except Exception as e:
            logger.error("Lege5.ro login error: %s", e)
            return False
