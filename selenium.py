from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def wait_for_ajax(driver, timeout):
    wait = WebDriverWait(driver, timeout)
    js_is_ajax_finished = 'return (!window.jQuery || window.jQuery.active == 0) && document.readyState == "complete"'
    wait.until(lambda d: d.execute_script(js_is_ajax_finished))


def locate_element(driver, xpath_or_id):
    els = driver.find_elements(By.XPATH if xpath_or_id.startswith('/') else By.ID, xpath_or_id)

    if not els:
        raise RuntimeError(f'cannot locate elements with xpath or id {xpath_or_id}')
    if len(els) > 1:
        raise RuntimeError(f'there are several elements with xpath or id {xpath_or_id}')

    return els[0]


def set_input(driver, xpath_or_id, text, clear_via_ctrl_a=False, send_tab=True):
    el = locate_element(driver, xpath_or_id)
    if clear_via_ctrl_a:
        el.send_keys(Keys.CONTROL + 'a')
    else:
        el.clear()
    el.send_keys(text)
    if send_tab:
        el.send_keys(Keys.TAB)
    current_text = el.get_attribute('value')
    if current_text != text:
        raise RuntimeError(f'cannot set text, current: {current_text}, expected: {text}')
