import os
import logging
import time
import urllib.request
import zipfile
from random import choice
from tempfile import NamedTemporaryFile
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.webdriver import DEFAULT_PORT
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement


DEFAULT_TIMEOUT = 60
DEFAULT_DIMENSIONS = (1280, 800)
DEFAULT_POSITION = (0, 0)
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/73.0.3683.103 Safari/537.36'
# noinspection HttpUrlsUsage
DEFAULT_URL_PING_TEST = 'http://ya.ru/'

CHROME_PROXY_EXT_TEMPFILE_PREFIX = '~chrome_proxy_ext_'
CHROME_PROXY_EXT_TEMPFILE_SUFFIX = '.tmp'

log = logging.getLogger(__name__)


def _test_proxy(proxy: str, url_ping_test: str = DEFAULT_URL_PING_TEST):
    proxy_support = urllib.request.ProxyHandler({'http': proxy})
    opener = urllib.request.build_opener(proxy_support)
    try:
        f = opener.open(url_ping_test)
        f.read(1)
        return True
    except OSError:
        return False


def _create_chrome_proxy_extension(proxy: str) -> NamedTemporaryFile:
    proxy_parts = proxy.split(':')
    port = proxy_parts[-1]
    user = proxy_parts[1][2:]
    password, host = proxy_parts[2].split('@')
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (host, port, user, password)

    tempfile = NamedTemporaryFile(prefix=CHROME_PROXY_EXT_TEMPFILE_PREFIX, suffix=CHROME_PROXY_EXT_TEMPFILE_SUFFIX)

    with zipfile.ZipFile(tempfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return tempfile


class ChromeEx(Chrome):
    def __init__(
            self, executable_path: str,
            port: int = DEFAULT_PORT,
            options: Options = None,
            extensions_base_dir: str = None,
            user_agent: str = DEFAULT_USER_AGENT,
            proxy: str = None,
            proxies_fallback: tuple[str] = (),
            headless: bool = True,
            dimensions: tuple[int, int] = DEFAULT_DIMENSIONS,
            position: tuple[int, int] = DEFAULT_POSITION,
            **kwargs):

        self._tempfile_proxy_chrome_extension = None

        if not options:
            options = Options()

        options.headless = headless
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ['enable-automation'])

        if extensions_base_dir:
            extensions_dirs = [f.path for f in os.scandir(extensions_base_dir) if f.is_dir()]
            if extensions_dirs:
                options.headless = False  # extensions do not work in headless mode
                options.add_argument(f'--load-extension={",".join(extensions_dirs)}')

        if proxy:
            if not proxies_fallback:
                raise RuntimeError(f'proxy without proxies_fallback given')

            if _test_proxy(proxy):
                log.info(f'Ping до ya.ru успешен, используем назначенный прокси {proxy}')
            else:
                proxy = choice(proxies_fallback)
                log.info(f'!!! Ping до ya.ru провален, используем резервный прокси {proxy}')

            if '@' not in proxy:
                # noinspection HttpUrlsUsage
                options.add_argument(f'--proxy-server={proxy.replace("http://", "")}')
            else:
                self._tempfile_proxy_chrome_extension = _create_chrome_proxy_extension(proxy)
                options.add_extension(self._tempfile_proxy_chrome_extension.name)

        options.add_argument(f'--window-size={dimensions[0]},{dimensions[1]}')
        options.add_argument('--disable-notifications')
        options.add_argument(f'user-agent="{user_agent}"')
        options.add_argument('disable-blink-features=AutomationControlled')

        super().__init__(executable_path=executable_path, port=port, options=options, **kwargs)

        self.set_window_size(*dimensions)
        self.set_window_position(*position)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            _ = 0
        super().__exit__(exc_type, exc_val, exc_tb)
        if self._tempfile_proxy_chrome_extension:
            self._tempfile_proxy_chrome_extension.__exit__(exc_type, exc_val, exc_tb)


def start_chrome(
        chrome_driver: str,
        extensions_base_dir: str = None,
        user_agent: str = DEFAULT_USER_AGENT,
        proxy_server: str = None,
        headless: bool = True,
        dimensions: tuple = DEFAULT_DIMENSIONS,
        position: tuple = DEFAULT_POSITION
) -> Chrome:
    """
    Deprecated. Use ChromeEx instead.
    """
    return ChromeEx(
        executable_path=chrome_driver, extensions_base_dir=extensions_base_dir, user_agent=user_agent,
        proxy=proxy_server, headless=headless, dimensions=dimensions, position=position
    )


def wait_for_ajax(driver, timeout: float = DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)
    js_is_ajax_finished = 'return (!window.jQuery || window.jQuery.active == 0) && document.readyState == "complete"'
    wait.until(lambda x: x.execute_script(js_is_ajax_finished))


class ChangesWaiter:
    def __init__(self, driver, xpath: str, timeout: float = DEFAULT_TIMEOUT):
        self.driver = driver
        self.xpath = xpath
        self.timeout = timeout

    def get_inner_htmls(self):
        ex_last = None
        for _ in range(10):
            try:
                result = [x.get_attribute('innerHTML') for x in self.driver.find_elements(By.XPATH, self.xpath)]
                return result
            except StaleElementReferenceException as ex:
                ex_last = ex
                time.sleep(0.1)
                pass
        raise ex_last

    def __enter__(self):
        self.inner_htmls = self.get_inner_htmls()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            WebDriverWait(self.driver, self.timeout).until(lambda x: self.inner_htmls != self.get_inner_htmls())


def wait_for_element(element, by: By, value: str, timeout: float = DEFAULT_TIMEOUT, msg: str = None):
    if element.find_elements(by=by, value=value):
        return

    if msg:
        log.info(msg)

    driver = getattr(element, 'parent', element)
    wait = WebDriverWait(driver, timeout)
    wait.until(lambda x: element.find_elements(by, value))


def wait_for_no_element(element, by: By, value: str, timeout: float = DEFAULT_TIMEOUT, msg: str = None):
    if not element.find_elements(by=by, value=value):
        return

    if msg:
        log.info(msg)

    driver = getattr(element, 'parent', element)
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(lambda x: not element.find_elements(by, value))
    except TimeoutException:
        raise


def wait_for_different_url(driver, url: str, timeout: float = DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)
    wait.until(lambda x: x.current_url != url)


def js_click(element, timeout: float = DEFAULT_TIMEOUT, wait_changes: bool = True, wait_ajax: bool = True):
    driver = element.parent
    src = driver.page_source
    driver.execute_script("arguments[0].click()", element)

    if wait_changes:
        def compare_source(d):
            try:
                return src != d.page_source
            except WebDriverException:
                pass

        WebDriverWait(driver, timeout).until(compare_source)

    if wait_ajax:
        wait_for_ajax(driver, timeout)


def locate_element(element, xpath_or_id: str, error_message: str = None) -> WebElement:
    if xpath_or_id.startswith('/') or xpath_or_id.startswith('./'):
        els = element.find_elements(By.XPATH, xpath_or_id)
    else:
        els = element.find_elements(By.ID, xpath_or_id)

    if error_message:
        error_message = error_message + ' - '
    if not els:
        raise RuntimeError(f'{error_message}cannot locate elements with xpath or id "{xpath_or_id}"')
    if len(els) > 1:
        raise RuntimeError(f'{error_message}there are several elements with xpath or id "{xpath_or_id}"')

    return els[0]


def set_input(
        driver, xpath_or_id: str, text: str, clear_via_ctrl_a: bool = False, send_tab: bool = True,
        not_found_error_msg: str = None, ignore_symbols: str = None, set_via_js: bool = False
):
    el = locate_element(driver, xpath_or_id, not_found_error_msg)
    if clear_via_ctrl_a:
        el.send_keys(Keys.CONTROL + 'a')
    else:
        el.clear()
    if set_via_js:
        driver.execute_script(f'arguments[0].value = "{text}"', el)
    else:
        el.send_keys(text)
    if send_tab:
        el.send_keys(Keys.TAB)
    current_text = el.get_attribute('value')
    if ignore_symbols:
        translate_dict = {ord(x): '' for x in ignore_symbols}
        current_text = current_text.translate(translate_dict)
        text = text.translate(translate_dict)
    if current_text != text:
        raise RuntimeError(f'cannot set text, current: "{current_text}", expected: "{text}"')
