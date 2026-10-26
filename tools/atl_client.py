"""Read-only Jira and Confluence Cloud client: login, API gateway fallback, pacing (MANTIS-IMP-087). Stdlib only.

    from atl_client import connect
    jira = connect("jira")            # or connect("confluence")
    data = jira.get("/rest/api/2/myself")

Keys come from mantis/config/.env (never committed): JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN and the
same three with CONFLUENCE_. An empty Confluence value falls back to the Jira one.

Read-only by construction: the only HTTP method this module can send is GET. Scoped API tokens
are refused on the site URL, so on a 401 the client looks up the site's cloud ID once (cached in
mantis/config/atlassian.json) and goes through https://api.atlassian.com/ex/<product>/<cloudId>.
Calls are paced (about four a second) and retried on 429 and 5xx, honouring Retry-After, so a
long run never floods the site. `calls` counts the requests a run made.
"""
import base64, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / "mantis" / "config" / ".env"
CONFIG = ROOT / "mantis" / "config" / "atlassian.json"
MIN_GAP = 0.25          # seconds between calls
RETRIES = 4


def load_env(path=ENV):
    """KEY=VALUE lines from the local .env; real environment variables win."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class AtlassianError(RuntimeError):
    pass


class Client:
    def __init__(self, product, site, email, token):
        self.product, self.site = product, site.rstrip("/").removesuffix("/wiki")
        self.prefix = "/wiki" if product == "confluence" else ""
        self.base = self.site + self.prefix
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.calls, self._last = 0, 0.0

    def _open(self, url, accept="application/json"):
        for attempt in range(RETRIES + 1):
            wait = MIN_GAP - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, method="GET", headers={"Authorization": self.auth, "Accept": accept})
            self._last, self.calls = time.monotonic(), self.calls + 1
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.read()
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or exc.code >= 500:
                    if attempt < RETRIES:
                        time.sleep(float(exc.headers.get("Retry-After") or 2 ** (attempt + 1)))
                        continue
                body = exc.read()[:300].decode("utf-8", "replace")
                raise AtlassianError(f"{exc.code} on {url.split('?')[0][-90:]}: {body}") from None
            except urllib.error.URLError as exc:
                if attempt < RETRIES:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise AtlassianError(f"network error: {exc.reason}") from None

    def url(self, path, params=None):
        if path.startswith("http"):
            return path
        q = ("?" + urllib.parse.urlencode(params, doseq=True)) if params else ""
        return self.base + path + q

    def get(self, path, params=None):
        return json.loads(self._open(self.url(path, params)) or b"{}")

    def get_bytes(self, path, params=None):
        return self._open(self.url(path, params), accept="*/*")

    def use_gateway(self):
        cfg = load_config()
        cid = cfg.get("cloud_id")
        if not cid:
            cid = json.loads(self._open(self.site + "/_edge/tenant_info"))["cloudId"]
            cfg["cloud_id"] = cid
            save_config(cfg)
        self.base = f"https://api.atlassian.com/ex/{self.product}/{cid}{self.prefix}"

    def whoami(self):
        path = "/rest/api/2/myself" if self.product == "jira" else "/rest/api/user/current"
        if load_config().get("cloud_id") and self.base.startswith(self.site):
            self.use_gateway()       # known scoped-token site: skip the failing first call
        try:
            return self.get(path).get("displayName", "?")
        except AtlassianError as exc:
            if not str(exc).startswith("401") or "api.atlassian.com" in self.base:
                raise
        self.use_gateway()
        return self.get(path).get("displayName", "?")


def connect(product):
    """A logged-in read-only client for "jira" or "confluence"."""
    load_env()
    up = product.upper()
    site = os.environ.get(f"{up}_URL") or os.environ.get("JIRA_URL")
    email = os.environ.get(f"{up}_EMAIL") or os.environ.get("JIRA_EMAIL")
    token = os.environ.get(f"{up}_API_TOKEN") or (os.environ.get("JIRA_API_TOKEN") if product == "confluence" else None)
    if not (site and email and token):
        raise AtlassianError(f"{up}_URL, {up}_EMAIL or {up}_API_TOKEN missing in mantis/config/.env")
    c = Client(product, site, email, token)
    try:
        c.user = c.whoami()
    except AtlassianError as exc:
        if str(exc).startswith("401"):
            raise AtlassianError(f"{product.title()} token rejected: update {up}_API_TOKEN in mantis/config/.env ({exc})") from None
        raise
    return c
