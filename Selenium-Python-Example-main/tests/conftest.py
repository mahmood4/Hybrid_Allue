from datetime import datetime

import allure
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
#from webdriver.chrome import ChromeDriverManager
#from webdriver.firefox import GeckoDriverManager

from pages.about_page import AboutPage
from pages.forgot_password_page import ForgotPasswordPage
from pages.login_page import LoginPage
from pages.project_edit_page import ProjectEditPage
from pages.project_type_page import ProjectTypePage
from pages.projects_page import ProjectsPage
from pages.templates_page import TemplatesPage
from utility.config_parser import AllureEnvironmentParser
from utility.config_parser import ConfigParserIni


# reads parameters from pytest command line
def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chrome", help="browser that the automation will run in")


def get_public_ip():
    return requests.get("http://checkip.amazonaws.com").text.rstrip()


@pytest.fixture(scope="session")
# instantiates ini file parses object
def prep_properties():
    config_reader = ConfigParserIni("props.ini")
    return config_reader


@pytest.fixture(autouse=True)
# fetch browser kind and base url then writes a dictionary of key-value pair into allure's environment.properties file
def write_allure_enviorment(prep_properties):
    yield
    env_parser = AllureEnvironmentParser("environment.properties")
    env_parser.write_to_allure_env({"browser": browser, "base_url": base_url})


# https://stackoverflow.com/a/61433141/4515129
@pytest.fixture
# Instantiates Page Objects
def pages():
    about_page = AboutPage(driver)
    projects_page = ProjectsPage(driver)
    forgot_password_page = ForgotPasswordPage(driver)
    login_page = LoginPage(driver)
    project_type_page = ProjectTypePage(driver)
    templates_page = TemplatesPage(driver)
    project_edit_page = ProjectEditPage(driver)
    return locals()


@pytest.fixture(autouse=True)
# Performs setup and tear down
def create_driver(write_allure_enviorment, prep_properties, request):
    global browser, base_url, driver
    browser = request.config.option.browser
    base_url = prep_properties.config_section_dict("Base Url")["base_url"]

    if browser == "firefox":
        driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
    elif browser == "remote":
        capabilities = {
            "browserName": "chrome",
            "browserVersion": "86.0",
            "selenoid:options": {
                "enableVNC": True,
                "enableVideo": False
            }
        }
        driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", desired_capabilities=capabilities)
    elif browser == "chrome_headless":
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
    else:
        driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.implicitly_wait(5)
    driver.maximize_window()
    driver.get(base_url)
    yield
    if request.node.rep_call.failed:
        screenshot_name = 'screenshot on failure: %s' % datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
        allure.attach(driver.get_screenshot_as_png(), name=screenshot_name,
                      attachment_type=allure.attachment_type.PNG)
        allure.attach(get_public_ip(), "public ip address", attachment_type=allure.attachment_type.TEXT)
    driver.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object

    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)
