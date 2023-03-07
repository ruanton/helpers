import os
import logging
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement


DEFAULT_TIMEOUT = 60
DEFAULT_DIMENSIONS = (1280, 800)
DEFAULT_POSITION = (0, 0)
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/73.0.3683.103 Safari/537.36'

log = logging.getLogger(__name__)


def start_chrome(
        chrome_driver: str,
        extensions_base_dir: str = None,
        user_agent: str = DEFAULT_USER_AGENT,
        proxy_server: str = None,
        headless: bool = True,
        dimensions: tuple = DEFAULT_DIMENSIONS,
        position: tuple = DEFAULT_POSITION) -> Chrome:

    opts = Options()
    opts.headless = headless

    opts.add_experimental_option('excludeSwitches', ['enable-logging'])
    opts.add_experimental_option("excludeSwitches", ['enable-automation'])

    if extensions_base_dir:
        extensions_dirs = [f.path for f in os.scandir(extensions_base_dir) if f.is_dir()]
        if extensions_dirs:
            opts.headless = False  # extensions do not work in headless mode
            opts.add_argument(f'--load-extension={",".join(extensions_dirs)}')

    opts.add_argument(f'--window-size={dimensions[0]},{dimensions[1]}')
    opts.add_argument('--disable-notifications')
    opts.add_argument(f'user-agent="{user_agent}"')
    opts.add_argument('disable-blink-features=AutomationControlled')

    if proxy_server:
        opts.add_argument(f'--proxy-server={proxy_server}')

    browser = Chrome(options=opts, executable_path=chrome_driver)

    browser.set_window_size(*dimensions)
    browser.set_window_position(*position)

    return browser


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
        return [x.get_attribute('innerHTML') for x in self.driver.find_elements(By.XPATH, self.xpath)]

    def __enter__(self):
        self.inner_htmls = self.get_inner_htmls()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            WebDriverWait(self.driver, self.timeout).until(lambda x: self.inner_htmls != self.get_inner_htmls())


def wait_for_element(driver, by: By, value: str, timeout: float = DEFAULT_TIMEOUT, msg: str = None):
    if driver.find_elements(by=by, value=value):
        return

    if msg:
        log.info(msg)

    wait = WebDriverWait(driver, timeout)
    wait.until(lambda x: x.find_elements(by, value))


def wait_for_no_element(driver, by: By, value: str, timeout: float = DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)
    wait.until(lambda x: not x.find_elements(by, value))


def wait_for_different_url(driver, url: str, timeout: float = DEFAULT_TIMEOUT):
    wait = WebDriverWait(driver, timeout)
    wait.until(lambda x: x.current_url != url )


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


def locate_element(driver, xpath_or_id: str, error_message: str = None) -> WebElement:
    if xpath_or_id.startswith('/') or xpath_or_id.startswith('./'):
        els = driver.find_elements(By.XPATH, xpath_or_id)
    else:
        els = driver.find_elements(By.ID, xpath_or_id)

    if error_message:
        error_message = error_message + ' - '
    if not els:
        raise RuntimeError(f'{error_message}cannot locate elements with xpath or id "{xpath_or_id}"')
    if len(els) > 1:
        raise RuntimeError(f'{error_message}there are several elements with xpath or id "{xpath_or_id}"')

    return els[0]


def set_input(
        driver, xpath_or_id: str, text: str, clear_via_ctrl_a: bool = False, send_tab: bool = True,
        not_found_error_msg: str = None, ignore_symbols: str = None, set_via_js:bool = False
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
