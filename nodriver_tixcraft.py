#!/usr/bin/env python3
#encoding=utf-8
import argparse
import base64
import json
import logging
import os
import pathlib
import platform
import random
import shutil
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import warnings
import webbrowser
from datetime import datetime
from typing import Optional

import nodriver as uc
from nodriver import cdp
from nodriver.core.config import Config
from urllib3.exceptions import InsecureRequestWarning

import util
from NonBrowser import NonBrowser

try:
    import ddddocr
except Exception as exc:
    print(exc)
    pass

CONST_APP_VERSION = "MaxBot (2024.08.03)"

CONST_MAXBOT_ANSWER_ONLINE_FILE = "MAXBOT_ONLINE_ANSWER.txt"
CONST_MAXBOT_CONFIG_FILE = "settings.json"
CONST_MAXBOT_EXTENSION_STATUS_JSON = "status.json"
CONST_MAXBOT_EXTENSION_NAME = "Maxbotplus_1.0.0"
CONST_MAXBOT_INT28_FILE = "MAXBOT_INT28_IDLE.txt"
CONST_MAXBOT_LAST_URL_FILE = "MAXBOT_LAST_URL.txt"
CONST_MAXBOT_QUESTION_FILE = "MAXBOT_QUESTION.txt"
CONST_MAXBLOCK_EXTENSION_NAME = "Maxblockplus_1.0.0"
CONST_MAXBLOCK_EXTENSION_FILTER =[
"*.doubleclick.net/*",
"*.ssp.hinet.net/*",
"*a.amnet.tw/*",
"*anymind360.com/*",
"*adx.c.appier.net/*",
"*cdn.cookielaw.org/*",
"*clarity.ms/*",
"*cloudfront.com/*",
"*cms.analytics.yahoo.com/*",
"*e2elog.fetnet.net/*",
"*fundingchoicesmessages.google.com/*",
"*ghtinc.com/*",
"*google-analytics.com/*",
"*googletagmanager.com/*",
"*googletagservices.com/*",
"*img.uniicreative.com/*",
"*lndata.com/*",
"*match.adsrvr.org/*",
"*onead.onevision.com.tw/*",
"*play.google.com/log?*",
"*popin.cc/*",
"*rollbar.com/*",
"*sb.scorecardresearch.com/*",
"*tagtoo.co/*",
"*ticketmaster.sg/js/adblock*",
"*ticketmaster.sg/js/adblock.js*",
"*tixcraft.com/js/analytics.js*",
"*tixcraft.com/js/common.js*",
"*tixcraft.com/js/custom.js*",
"*treasuredata.com/*",
"*www.youtube.com/youtubei/v1/player/heartbeat*",
]

CONST_CITYLINE_SIGN_IN_URL = "https://www.cityline.com/Login.html?targetUrl=https%3A%2F%2Fwww.cityline.com%2FEvents.html"
CONST_FAMI_SIGN_IN_URL = "https://www.famiticket.com.tw/Home/User/SignIn"
CONST_HKTICKETING_SIGN_IN_URL = "https://premier.hkticketing.com/Secure/ShowLogin.aspx"
CONST_KHAM_SIGN_IN_URL = "https://kham.com.tw/application/UTK13/UTK1306_.aspx"
CONST_KKTIX_SIGN_IN_URL = "https://kktix.com/users/sign_in?back_to=%s"
CONST_TICKET_SIGN_IN_URL = "https://ticket.com.tw/application/utk13/utk1306_.aspx"
CONST_URBTIX_SIGN_IN_URL = "https://www.urbtix.hk/member-login"

CONST_FROM_TOP_TO_BOTTOM = "from top to bottom"
CONST_FROM_BOTTOM_TO_TOP = "from bottom to top"
CONST_CENTER = "center"
CONST_RANDOM = "random"
CONST_SELECT_ORDER_DEFAULT = CONST_FROM_TOP_TO_BOTTOM

CONT_STRING_1_SEATS_REMAINING = ['@1 seat(s) remaining','剩餘 1@','@1 席残り']

CONST_OCR_CAPTCH_IMAGE_SOURCE_NON_BROWSER = "NonBrowser"
CONST_OCR_CAPTCH_IMAGE_SOURCE_CANVAS = "canvas"

CONST_WEBDRIVER_TYPE_NODRIVER = "nodriver"
CONST_CHROME_FAMILY = ["chrome","edge","brave"]

warnings.simplefilter('ignore',InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context
logging.basicConfig()
logger = logging.getLogger('logger')


def get_config_dict(args):
    app_root = util.get_app_root()
    config_filepath = os.path.join(app_root, CONST_MAXBOT_CONFIG_FILE)

    # allow assign config by command line.
    if args.input and len(args.input) > 0:
        config_filepath = args.input

    config_dict = None
    if os.path.isfile(config_filepath):
        # start to overwrite config settings.
        with open(config_filepath) as json_data:
            config_dict = json.load(json_data)

            # Define a dictionary to map argument names to their paths in the config_dict
            arg_to_path = {
                "headless": ["advanced", "headless"],
                "homepage": ["homepage"],
                "ticket_number": ["ticket_number"],
                "browser": ["browser"],
                "tixcraft_sid": ["advanced", "tixcraft_sid"],
                "ibonqware": ["advanced", "ibonqware"],
                "kktix_account": ["advanced", "kktix_account"],
                "kktix_password": ["advanced", "kktix_password_plaintext"],
                "proxy_server": ["advanced", "proxy_server_port"],
                "window_size": ["advanced", "window_size"]
            }

            # Update the config_dict based on the arguments
            for arg, path in arg_to_path.items():
                value = getattr(args, arg)
                if value and len(str(value)) > 0:
                    d = config_dict
                    for key in path[:-1]:
                        d = d[key]
                    d[path[-1]] = value

            # special case for headless to enable away from keyboard mode.
            is_headless_enable_ocr = False
            if config_dict["advanced"]["headless"]:
                # for tixcraft headless.
                if len(config_dict["advanced"]["tixcraft_sid"]) > 1:
                    is_headless_enable_ocr = True

            if is_headless_enable_ocr:
                config_dict["ocr_captcha"]["enable"] = True
                config_dict["ocr_captcha"]["force_submit"] = True

    return config_dict

def write_question_to_file(question_text):
    working_dir = os.path.dirname(os.path.realpath(__file__))
    target_path = os.path.join(working_dir, CONST_MAXBOT_QUESTION_FILE)
    util.write_string_to_file(target_path, question_text)

def write_last_url_to_file(url):
    working_dir = os.path.dirname(os.path.realpath(__file__))
    target_path = os.path.join(working_dir, CONST_MAXBOT_LAST_URL_FILE)
    util.write_string_to_file(target_path, url)

def read_last_url_from_file():
    ret = ""
    with open(CONST_MAXBOT_LAST_URL_FILE, "r") as text_file:
        ret = text_file.readline()
    return ret

def sync_status_to_extension(status):
    # sync generated ext status.
    Root_Dir = util.get_app_root()
    webdriver_folder = os.path.join(Root_Dir, "webdriver")
    target_folder_list = os.listdir(webdriver_folder)
    for item in target_folder_list:
        if item.startswith("tmp_" + CONST_MAXBOT_EXTENSION_NAME):
            target_path = os.path.join(webdriver_folder, item)
            target_path = os.path.join(target_path, "data")
            if os.path.exists(target_path):
                target_path = os.path.join(target_path, CONST_MAXBOT_EXTENSION_STATUS_JSON)
                #print("save as to:", target_path)
                status_json={}
                status_json["status"]=status
                #print("dump json to path:", target_path)
                try:
                    with open(target_path, 'w') as outfile:
                        json.dump(status_json, outfile)
                except Exception as e:
                    pass

def play_sound_while_ordering(config_dict):
    app_root = util.get_app_root()
    captcha_sound_filename = os.path.join(app_root, config_dict["advanced"]["play_sound"]["filename"].strip())
    util.play_mp3_async(captcha_sound_filename)

async def nodriver_press_button(tab, select_query):
    ret = False
    if tab:
        try:
            element = await tab.query_selector(select_query)
            if element:
                await element.click()
                ret = True
            else:
                #print("element not found:", select_query)
                pass
        except Exception as e:
            #print("click fail for selector:", select_query)
            print(e)
            pass
    return ret

async def nodriver_check_checkbox(tab: Optional[object], select_query: str, value: str = 'true') -> bool:
    if tab:
        try:
            element = await tab.query_selector(select_query)
            if element:
                await element.click()
                return True
        except Exception as exc:
            print(exc)
    return False

async def nodriver_facebook_login(tab, facebook_account, facebook_password):
    if tab:
        try:
            account = await tab.query_selector("#email")
            if account:
                await account.send_keys(facebook_account)
            else:
                print("account not found")

            password = await tab.query_selector("#pass")
            if password:
                await password.send_keys(facebook_password)
                await tab.send(cdp.input_.dispatch_key_event("keyDown", code="Enter", key="Enter", text="\r", windows_virtual_key_code=13))
                await tab.send(cdp.input_.dispatch_key_event("keyUp", code="Enter", key="Enter", text="\r", windows_virtual_key_code=13))
                time.sleep(2)
            else:
                print("password not found")
        except Exception as e:
            print("send_keys fail.")
            print(e)
            pass


async def nodriver_kktix_signin(tab, url, config_dict):
    # for like human.
    time.sleep(5)

    kktix_account = config_dict["advanced"]["kktix_account"]
    kktix_password = config_dict["advanced"]["kktix_password_plaintext"].strip()
    if kktix_password == "":
        kktix_password = util.decrypt_me(config_dict["advanced"]["kktix_password"])
    if len(kktix_account) > 4:
        try:
            account = await tab.query_selector("#user_login")
            await account.send_keys(kktix_account)

            password = await tab.query_selector("#user_password")
            await password.send_keys(kktix_password)

            submit = await tab.query_selector("input[type='submit'][name]")
            await submit.click()
            time.sleep(0.2)
        except Exception as e:
            print(e)
            pass

async def nodriver_kktix_paused_main(tab, url, config_dict):
    is_url_contain_sign_in = False
    # fix https://kktix.com/users/sign_in?back_to=https://kktix.com/events/xxxx and registerStatus: SOLD_OUT cause page refresh.
    if '/users/sign_in?' in url:
        await nodriver_kktix_signin(tab, url, config_dict)
        is_url_contain_sign_in = True

async def nodriver_goto_homepage(driver, config_dict):
    homepage = config_dict["homepage"]
    tab = None

    if 'kktix.c' in homepage:
        # for like human.
        try:
            tab = await driver.get(homepage)
            await driver
            await driver.sleep(5)
        except Exception as e:
            pass

        if len(config_dict["advanced"]["kktix_account"])>0:
            if not 'https://kktix.com/users/sign_in?' in homepage:
                homepage = CONST_KKTIX_SIGN_IN_URL % (homepage)

    if 'famiticket.com' in homepage:
        if len(config_dict["advanced"]["fami_account"])>0:
            homepage = CONST_FAMI_SIGN_IN_URL

    if 'kham.com' in homepage:
        if len(config_dict["advanced"]["kham_account"])>0:
            homepage = CONST_KHAM_SIGN_IN_URL

    if 'ticket.com.tw' in homepage:
        if len(config_dict["advanced"]["ticket_account"])>0:
            homepage = CONST_TICKET_SIGN_IN_URL

    if 'urbtix.hk' in homepage:
        if len(config_dict["advanced"]["urbtix_account"])>0:
            homepage = CONST_URBTIX_SIGN_IN_URL

    if 'cityline.com' in homepage:
        if len(config_dict["advanced"]["cityline_account"])>0:
            homepage = CONST_CITYLINE_SIGN_IN_URL

    if 'hkticketing.com' in homepage:
        if len(config_dict["advanced"]["hkticketing_account"])>0:
            homepage = CONST_HKTICKETING_SIGN_IN_URL

    if 'ticketplus.com.tw' in homepage:
        if len(config_dict["advanced"]["ticketplus_account"]) > 1:
            homepage = "https://ticketplus.com.tw/"

    try:
        tab = await driver.get(homepage)
        await driver
        await driver.sleep(5)
    except Exception as e:
        pass

    tixcraft_family = False
    if 'tixcraft.com' in homepage:
        tixcraft_family = True

    if 'indievox.com' in homepage:
        tixcraft_family = True

    if 'ticketmaster.' in homepage:
        tixcraft_family = True

    if tixcraft_family:
        tixcraft_sid = config_dict["advanced"]["tixcraft_sid"]
        if len(tixcraft_sid) > 1:
            domain_name = homepage.split('/')[2]
            cookies  = await driver.cookies.get_all()
            is_cookie_exist = False
            for cookie in cookies:
                if cookie.name=='SID':
                    cookie.value=tixcraft_sid
                    is_cookie_exist = True
                    break

            is_cookie_changed = False
            if not is_cookie_exist:
                new_cookie = cdp.network.CookieParam("SID",tixcraft_sid, domain=domain_name, path="/", http_only=True, secure=True)
                cookies.append(new_cookie)
                is_cookie_changed = True
            await driver.cookies.set_all(cookies)

            if is_cookie_changed:
                try:
                    for each_tab in driver.tabs:
                        await each_tab.reload()
                except Exception as exc:
                    print(exc)
                    pass

    if 'ibon.com' in homepage:
        ibonqware = config_dict["advanced"]["ibonqware"]
        if len(ibonqware) > 1:
            cookies  = await driver.cookies.get_all()
            is_cookie_exist = False
            for cookie in cookies:
                if cookie.name=='ibonqware':
                    cookie.value=ibonqware
                    is_cookie_exist = True
                    break
            if not is_cookie_exist:
                new_cookie = cdp.network.CookieParam("ibonqware",ibonqware, domain=".ibon.com.tw", path="/", http_only=True, secure=True)
                cookies.append(new_cookie)
            await driver.cookies.set_all(cookies)

        if 'https://ticket.ibon.com.tw/ActivityInfo/Details/' in homepage:
            #如果首頁設在 https://ticket.ibon.com.tw/ActivityInfo/Details/xxxx, 日期頁面, 透過程式自動按一次重新整理頁面(F5).
            time.sleep(3)
            try:
                for each_tab in driver.tabs:
                    await each_tab.reload()
            except Exception as exc:
                print(exc)
                pass


    return tab

async def nodriver_kktix_travel_price_list(tab, config_dict, kktix_area_auto_select_mode, kktix_area_keyword):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    ticket_number = config_dict["ticket_number"]

    areas = None
    is_ticket_number_assigned = False

    ticket_price_list = None
    try:
        ticket_price_list = await tab.query_selector_all('div.display-table-row')
    except Exception as exc:
        ticket_price_list = None
        print("find ticket-price Exception:")
        print(exc)
        pass

    is_dom_ready = True
    price_list_count = 0
    if not ticket_price_list is None:
        price_list_count = len(ticket_price_list)
        if show_debug_message:
            print("found price count:", price_list_count)
    else:
        is_dom_ready = False
        print("find ticket-price fail")

    if price_list_count > 0:
        areas = []

        kktix_area_keyword_array = kktix_area_keyword.split(' ')
        kktix_area_keyword_1 = kktix_area_keyword_array[0]
        kktix_area_keyword_1_and = ""
        if len(kktix_area_keyword_array) > 1:
            kktix_area_keyword_1_and = kktix_area_keyword_array[1]

        # clean stop word.
        kktix_area_keyword_1 = util.format_keyword_string(kktix_area_keyword_1)
        kktix_area_keyword_1_and = util.format_keyword_string(kktix_area_keyword_1_and)

        if show_debug_message:
            print('kktix_area_keyword_1:', kktix_area_keyword_1)
            print('kktix_area_keyword_1_and:', kktix_area_keyword_1_and)

        for row in ticket_price_list:
            row_text = ""
            row_html = ""
            row_input = None
            current_ticket_number = "0"
            try:
                #js_attr = await row.get_js_attributes()
                row_html = await row.get_html()
                row_text = util.remove_html_tags(row_html)

                row_input = await row.query_selector("input")
                if row_input:
                    js_attr_input = await row_input.get_js_attributes()
                    if js_attr_input:
                        current_ticket_number = js_attr_input["value"]
            except Exception as exc:
                is_dom_ready = False
                if show_debug_message:
                    print(exc)
                # error, exit loop
                break

            if len(row_text) > 0:
                if '未開賣' in row_text:
                    row_text = ""

                if '暫無票' in row_text:
                    row_text = ""

                if '已售完' in row_text:
                    row_text = ""

                if 'Sold Out' in row_text:
                    row_text = ""

                if '完売' in row_text:
                    row_text = ""

                if not('<input type=' in row_html):
                    row_text = ""

            if len(row_text) > 0:
                if util.reset_row_text_if_match_keyword_exclude(config_dict, row_text):
                    row_text = ""

            if len(row_text) > 0:
                # clean stop word.
                row_text = util.format_keyword_string(row_text)

            if len(row_text) > 0:
                if ticket_number > 1:
                    # start to check danger notice.
                    # 剩 n 張票 / n Left / 残り n 枚
                    ticket_count = 999
                    # for cht.
                    if ' danger' in row_html and '剩' in row_text and '張' in row_text:
                        tmp_array = row_html.split('剩')
                        tmp_array = tmp_array[1].split('張')
                        if len(tmp_array) > 0:
                            tmp_ticket_count = tmp_array[0].strip()
                            if tmp_ticket_count.isdigit():
                                ticket_count = int(tmp_ticket_count)
                                if show_debug_message:
                                    print("found ticket 剩:", tmp_ticket_count)
                    # for ja.
                    if ' danger' in row_html and '残り' in row_text and '枚' in row_text:
                        tmp_array = row_html.split('残り')
                        tmp_array = tmp_array[1].split('枚')
                        if len(tmp_array) > 0:
                            tmp_ticket_count = tmp_array[0].strip()
                            if tmp_ticket_count.isdigit():
                                ticket_count = int(tmp_ticket_count)
                                if show_debug_message:
                                    print("found ticket 残り:", tmp_ticket_count)
                    # for en.
                    if ' danger' in row_html and ' Left ' in row_html:
                        tmp_array = row_html.split(' Left ')
                        tmp_array = tmp_array[0].split('>')
                        if len(tmp_array) > 0:
                            tmp_ticket_count = tmp_array[len(tmp_array)-1].strip()
                            if tmp_ticket_count.isdigit():
                                if show_debug_message:
                                    print("found ticket left:", tmp_ticket_count)
                                ticket_count = int(tmp_ticket_count)

                    if ticket_count < ticket_number:
                        # skip this row, due to no ticket remaining.
                        if show_debug_message:
                            print("found ticket left:", tmp_ticket_count, ",but target ticket:", ticket_number)
                        row_text = ""

            if not row_input is None:
                is_match_area = False

                # check ticket input textbox.
                if len(current_ticket_number) > 0:
                    if current_ticket_number != "0":
                        is_ticket_number_assigned = True

                if is_ticket_number_assigned:
                    # no need to travel
                    break

                if len(kktix_area_keyword_1) == 0:
                    # keyword #1, empty, direct add to list.
                    is_match_area = True
                    match_area_code = 1
                else:
                    # MUST match keyword #1.
                    if kktix_area_keyword_1 in row_text:
                        #print('match keyword#1')

                        # because of logic between keywords is AND!
                        if len(kktix_area_keyword_1_and) == 0:
                            #print('keyword#2 is empty, directly match.')
                            # keyword #2 is empty, direct append.
                            is_match_area = True
                            match_area_code = 2
                        else:
                            if kktix_area_keyword_1_and in row_text:
                                #print('match keyword#2')
                                is_match_area = True
                                match_area_code = 3
                            else:
                                #print('not match keyword#2')
                                pass
                    else:
                        #print('not match keyword#1')
                        pass

                if show_debug_message:
                    print("is_match_area:", is_match_area)
                    print("match_area_code:", match_area_code)

                if is_match_area:
                    areas.append(row_input)

                    # from top to bottom, match first to break.
                    if kktix_area_auto_select_mode == CONST_FROM_TOP_TO_BOTTOM:
                        break

            if not is_dom_ready:
                # not sure to break or continue..., maybe break better.
                break
    else:
        if show_debug_message:
            print("no any price list found.")
        pass

    return is_dom_ready, is_ticket_number_assigned, areas


async def nodriver_kktix_assign_ticket_number(tab, config_dict, kktix_area_keyword):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    ticket_number_str = str(config_dict["ticket_number"])
    auto_select_mode = config_dict["area_auto_select"]["mode"]

    is_ticket_number_assigned = False
    matched_blocks = None
    is_dom_ready = True
    is_dom_ready, is_ticket_number_assigned, matched_blocks = await nodriver_kktix_travel_price_list(tab, config_dict, auto_select_mode, kktix_area_keyword)

    target_area = None
    is_need_refresh = False
    if is_dom_ready:
        if not is_ticket_number_assigned:
            target_area = util.get_target_item_from_matched_list(matched_blocks, auto_select_mode)

        if not matched_blocks is None:
            if len(matched_blocks) == 0:
                is_need_refresh = True
                if show_debug_message:
                    print("matched_blocks is empty, is_need_refresh")

    if not target_area is None:
        current_ticket_number = ""
        if show_debug_message:
            print("try to set input box value.")
        try:
            current_ticket_number = await target_area.apply('function (element) { return element.value; } ')
        except Exception as exc:
            pass

        if show_debug_message:
            print("current_ticket_number", current_ticket_number)

        if len(current_ticket_number) > 0:
            if current_ticket_number == "0":
                try:
                    print("asssign ticket number:%s" % ticket_number_str)
                    await target_area.click()
                    await target_area.apply('function (element) {element.value = ""; } ')
                    await target_area.send_keys(ticket_number_str);
                    is_ticket_number_assigned = True
                except Exception as exc:
                    print("asssign ticket number to ticket-price field Exception:")
                    print(exc)
            else:
                if show_debug_message:
                    print("value already assigned.")
                # already assigned.
                is_ticket_number_assigned = True

    return is_dom_ready, is_ticket_number_assigned, is_need_refresh


async def nodriver_kktix_reg_captcha(tab, config_dict, fail_list, registrationsNewApp_div):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    answer_list = []

    is_question_popup = False
    question_text = await nodriver_get_text_by_selector(tab, 'div.custom-captcha-inner p', 'innerText')
    if len(question_text) > 0:
        is_question_popup = True
        write_question_to_file(question_text)

        answer_list = util.get_answer_list_from_user_guess_string(config_dict, CONST_MAXBOT_ANSWER_ONLINE_FILE)
        if len(answer_list)==0:
            if config_dict["advanced"]["auto_guess_options"]:
                #answer_list = util.get_answer_list_from_question_string(registrationsNewApp_div, question_text)
                # due to selenium forat.
                answer_list = util.get_answer_list_from_question_string(None, question_text)

        inferred_answer_string = ""
        for answer_item in answer_list:
            if not answer_item in fail_list:
                inferred_answer_string = answer_item
                break

        if len(answer_list) > 0:
            answer_list = list(dict.fromkeys(answer_list))

        if show_debug_message:
            print("inferred_answer_string:", inferred_answer_string)
            print("question_text:", question_text)
            print("answer_list:", answer_list)
            print("fail_list:", fail_list)

        # PS: auto-focus() when empty inferred_answer_string with empty inputed text value.
        if len(inferred_answer_string) > 0:
            input_text_css = 'div.custom-captcha-inner > div > div > input'
            next_step_button_css = ''
            submit_by_enter = False
            check_input_interval = 0.2
            #is_answer_sent, fail_list = fill_common_verify_form(tab, config_dict, inferred_answer_string, fail_list, input_text_css, next_step_button_css, submit_by_enter, check_input_interval)
            if len(answer_list) > 0:
                input_text = await tab.query_selector(input_text_css)
                if not input_text is None:

                    await input_text.click()
                    await input_text.apply('function (element) {element.value = ""; } ')
                    await input_text.send_keys(inferred_answer_string)
                    time.sleep(0.1)

                    # due multi next buttons(pick seats/best seats)
                    print("click")
                    await nodriver_kktix_press_next_button(tab)
                    time.sleep(0.75)

                    fail_list.append(inferred_answer_string)


    return fail_list, is_question_popup

#   : This is for case-2 next button.
async def nodriver_kktix_press_next_button(tab):
    ret = False

    css_select = "div.register-new-next-button-area > button"
    but_button_list = None
    try:
        but_button_list = await tab.query_selector_all(css_select)
    except Exception as exc:
        print(exc)
        pass

    if not but_button_list is None:
        button_count = len(but_button_list)
        #print("button_count:",button_count)
        if button_count > 0:
            try:
                #print("click on last button")
                await but_button_list[button_count-1].click()
                time.sleep(0.3)
                ret = True
            except Exception as exc:
                print(exc)
                pass

    return ret


async def nodriver_kktix_reg_new_main(tab, url, config_dict, fail_list, played_sound_ticket, last_sent_minute):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    # read config.
    area_keyword = config_dict["area_auto_select"]["area_keyword"].strip()

    # part 1: check div.
    registrationsNewApp_div = None
    try:
        registrationsNewApp_div = await tab.query_selector('#registrationsNewApp')
    except Exception as exc:
        pass
        #print("find input fail:", exc)

    # part 2: assign ticket number
    is_ticket_number_assigned = False
    if not registrationsNewApp_div is None:
        is_dom_ready = True
        is_need_refresh = False

        if len(area_keyword) > 0:
            area_keyword_array = []
            try:
                area_keyword_array = json.loads("["+ area_keyword +"]")
            except Exception as exc:
                area_keyword_array = []

            # default refresh
            is_need_refresh_final = True

            for area_keyword_item in area_keyword_array:
                is_need_refresh_tmp = False
                is_dom_ready, is_ticket_number_assigned, is_need_refresh_tmp = await nodriver_kktix_assign_ticket_number(tab, config_dict, area_keyword_item)

                if not is_dom_ready:
                    # page redirecting.
                    break

                # one of keywords not need to refresh, final is not refresh.
                if not is_need_refresh_tmp:
                    is_need_refresh_final = False

                if is_ticket_number_assigned:
                    break
                else:
                    if show_debug_message:
                        print("is_need_refresh for keyword:", area_keyword_item)

            if not is_ticket_number_assigned:
                is_need_refresh = is_need_refresh_final
        else:
            # empty keyword, match all.
            # TODO:
            is_dom_ready, is_ticket_number_assigned, is_need_refresh = await nodriver_kktix_assign_ticket_number(tab, config_dict, "")
            pass

        if is_dom_ready:
            # part 3: captcha
            if is_ticket_number_assigned:
                if config_dict["advanced"]["play_sound"]["ticket"]:
                    if not played_sound_ticket:
                        play_sound_while_ordering(config_dict)
                    played_sound_ticket = True

                last_sent_minute = util.optimized_email_sending(config_dict, "ticket", last_sent_minute, url)

                is_finish_checkbox_click = await nodriver_check_checkbox(tab, 'input[type="checkbox"]:not(:checked)')

                # whole event question.
                fail_list, is_question_popup = await nodriver_kktix_reg_captcha(tab, config_dict, fail_list, registrationsNewApp_div)

                # single option question
                if not is_question_popup:
                    # no captcha text popup, goto next page.
                    control_text = await nodriver_get_text_by_selector(tab, 'div > div.code-input > div.control-group > label.control-label', 'innerText')
                    if show_debug_message:
                        print("control_text:", control_text)

                    if len(control_text) > 0:
                        input_text_css = 'div > div.code-input > div.control-group > div.controls > label[ng-if] > input[type="text"]'
                        input_text_element = None
                        try:
                            input_text_element = await tab.query_selector(input_text_css)
                        except Exception as exc:
                            #print(exc)
                            pass
                        if input_text_element is None:
                            radio_css = 'div > div.code-input > div.control-group > div.controls > label[ng-if] > input[type="radio"]'
                            try:
                                radio_element = await tab.query_selector(radio_css)
                                if radio_element:
                                    print("found radio")
                                    joined_button_css = 'div > div.code-input > div.control-group > div.controls > label[ng-if] > span[ng-if] > a[ng-href="#"]'
                                    joined_element = await tab.query_selector(joined_button_css)
                                    if joined_element:
                                        control_text = ""
                                        print("member joined")
                            except Exception as exc:
                                print(exc)
                                pass

                    if len(control_text) == 0:
                        if config_dict["kktix"]["auto_press_next_step_button"]:
                            click_ret = await nodriver_kktix_press_next_button(tab)
                    else:
                        # input by maxbox plus extension.
                        is_fill_at_webdriver = False

                        if not config_dict["browser"] in CONST_CHROME_FAMILY:
                            is_fill_at_webdriver = True
                        else:
                            if not config_dict["advanced"]["chrome_extension"]:
                                is_fill_at_webdriver = True

                        # TODO: not implement in extension, so force to fill in webdriver.
                        is_fill_at_webdriver = True
                        if is_fill_at_webdriver:
                            #TODO:
                            #set_kktix_control_label_text(driver, config_dict)
                            pass
            else:
                if is_need_refresh:
                    # reset to play sound when ticket avaiable.
                    played_sound_ticket = False

                    try:
                        print("no match any price, start to refresh page...")
                        await tab.reload()
                    except Exception as exc:
                        #print("refresh fail")
                        pass

                    if config_dict["advanced"]["auto_reload_page_interval"] > 0:
                        time.sleep(config_dict["advanced"]["auto_reload_page_interval"])

    return fail_list, played_sound_ticket, last_sent_minute

async def nodriver_kktix_main(tab, url, config_dict):
    global kktix_dict
    if not 'kktix_dict' in globals():
        kktix_dict = {}
        kktix_dict["fail_list"]=[]
        kktix_dict["start_time"]=None
        kktix_dict["done_time"]=None
        kktix_dict["elapsed_time"]=None
        kktix_dict["is_popup_checkout"] = False
        kktix_dict["played_sound_ticket"] = False
        kktix_dict["played_sound_order"] = False
        kktix_dict["last_sent_minute"] = None

    is_url_contain_sign_in = False
    # fix https://kktix.com/users/sign_in?back_to=https://kktix.com/events/xxxx and registerStatus: SOLD_OUT cause page refresh.
    if '/users/sign_in?' in url:
        await nodriver_kktix_signin(tab, url, config_dict)
        is_url_contain_sign_in = True

    if not is_url_contain_sign_in:
        if '/registrations/new' in url:
            kktix_dict["start_time"] = time.time()

            is_dom_ready = False
            try:
                html_body = await tab.get_content()
                #print("html_body:",len(html_body))
                if html_body:
                    if len(html_body) > 10240:
                        if "registrationsNewApp" in html_body:
                            if not "{{'new.i_read_and_agree_to'" in html_body:
                                is_dom_ready = True
            except Exception as exc:
                #print(exc)
                pass

            if not is_dom_ready:
                # reset answer fail list.
                kktix_dict["fail_list"] = []
                kktix_dict["played_sound_ticket"] = False
            else:
                is_finish_checkbox_click = False
                #TODO: check checkbox here.

                # check is able to buy.
                if config_dict["kktix"]["auto_fill_ticket_number"]:
                    kktix_dict["fail_list"], kktix_dict["played_sound_ticket"], kktix_dict["last_sent_minute"] = await nodriver_kktix_reg_new_main(tab, url, config_dict, kktix_dict["fail_list"], kktix_dict["played_sound_ticket"], kktix_dict["last_sent_minute"])
                    kktix_dict["done_time"] = time.time()
        else:
            is_event_page = False
            if '/events/' in url:
                # ex: https://xxx.kktix.cc/events/xxx-copy-1
                if len(url.split('/'))<=5:
                    is_event_page = True

            if is_event_page:
                if config_dict["kktix"]["auto_press_next_step_button"]:
                    # pass switch check.
                    #print("should press next here.")
                    #kktix_events_press_next_button(driver)
                    pass

            # reset answer fail list.
            kktix_dict["fail_list"] = []
            kktix_dict["played_sound_ticket"] = False

    is_kktix_got_ticket = False
    if '/events/' in url and '/registrations/' in url and "-" in url:
        if not '/registrations/new' in url:
            if not 'https://kktix.com/users/sign_in?' in url:
                is_kktix_got_ticket = True

    if is_kktix_got_ticket:
        if '/events/' in config_dict["homepage"] and '/registrations/' in config_dict["homepage"] and "-" in config_dict["homepage"]:
            # do nothing when second time come in.
            if len(url.split('/'))>=7:
                if len(config_dict["homepage"].split('/'))>=7:
                    # match event code.
                    if url.split('/')[4]==config_dict["homepage"].split('/')[4]:
                        # break loop.
                        is_kktix_got_ticket = False

    is_quit_bot = False
    if is_kktix_got_ticket:
        if not kktix_dict["start_time"] is None:
            if not kktix_dict["done_time"] is None:
                bot_elapsed_time = kktix_dict["done_time"] - kktix_dict["start_time"]
                if kktix_dict["elapsed_time"] != bot_elapsed_time:
                    print("bot elapsed time:", "{:.3f}".format(bot_elapsed_time))
                kktix_dict["elapsed_time"] = bot_elapsed_time

        if config_dict["advanced"]["play_sound"]["order"]:
            if not kktix_dict["played_sound_order"]:
                play_sound_while_ordering(config_dict)
        util.optimized_email_sending(config_dict, "order", None, url)

        kktix_dict["played_sound_order"] = True

        if config_dict["advanced"]["headless"]:
            if not kktix_dict["is_popup_checkout"]:
                kktix_account = config_dict["advanced"]["kktix_account"]
                kktix_password = config_dict["advanced"]["kktix_password_plaintext"].strip()
                if kktix_password == "":
                    kktix_password = util.decrypt_me(config_dict["advanced"]["kktix_password"])

                print("基本資料(或實名制)網址:", url)
                if len(kktix_account) > 0:
                    print("搶票成功, 帳號:", kktix_account)

                    script_name = "chrome_tixcraft"
                    if config_dict["webdriver_type"] == CONST_WEBDRIVER_TYPE_NODRIVER:
                        script_name = "nodriver_tixcraft"

                    threading.Thread(target=util.launch_maxbot, args=(script_name,"", url, kktix_account, kktix_password,"","false",)).start()
                    #driver.quit()
                    #sys.exit()

                is_event_page = False
                if len(url.split('/'))>=7:
                    is_event_page = True
                if is_event_page:
                    confirm_clicked = False

                    try:
                        submit = await tab.query_selector("div.form-actions a.btn-primary")
                        await submit.click()
                        confirm_clicked = True
                    except Exception as exc:
                        print(exc)

                    if confirm_clicked:
                        domain_name = url.split('/')[2]
                        checkout_url = "https://%s/account/orders" % (domain_name)
                        print("搶票成功, 請前往該帳號訂單查看: %s" % (checkout_url))
                        webbrowser.open_new(checkout_url)

                kktix_dict["is_popup_checkout"] = True
                is_quit_bot = True
    else:
        kktix_dict["is_popup_checkout"] = False
        kktix_dict["played_sound_order"] = False

    return is_quit_bot

async def nodriver_tixcraft_home_close_window(tab):
    accept_all_cookies_btn = None
    try:
        accept_all_cookies_btn = await tab.query_selector('#onetrust-accept-btn-handler')
        if accept_all_cookies_btn:
            accept_all_cookies_btn.click()
    except Exception as exc:
        #print(exc)
        pass

async def nodriver_get_text_by_selector(tab, my_css_selector, attribute='innerHTML'):
    div_text = ""
    try:
        div_element = await tab.query_selector(my_css_selector)
        if div_element:
            #js_attr = await div_element.get_js_attributes()
            div_text = await div_element.get_html()

            # only this case to remove tags
            if attribute=="innerText":
                div_text = util.remove_html_tags(div_text)
    except Exception as exc:
        print("find verify textbox fail")
        pass

    return div_text

async def nodriver_tixcraft_redirect(tab, url):
    ret = False
    game_name = ""
    url_split = url.split("/")
    if len(url_split) >= 6:
        game_name = url_split[5]
    if len(game_name) > 0:
        if "/activity/detail/%s" % (game_name,) in url:
            entry_url = url.replace("/activity/detail/","/activity/game/")
            print("redirec to new url:", entry_url)
            try:
                await tab.get(entry_url)
                ret = True
            except Exception as exec1:
                pass
    return ret

async def nodriver_ticketmaster_promo(tab, config_dict, fail_list):
    question_selector = '#promoBox'
    return nodriver_tixcraft_input_check_code(tab, config_dict, fail_list, question_selector)

async def nodriver_tixcraft_verify(tab, config_dict, fail_list):
    question_selector = '.zone-verify'
    return nodriver_tixcraft_input_check_code(tab, config_dict, fail_list, question_selector)

async def nodriver_tixcraft_input_check_code(tab, config_dict, fail_list, question_selector):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    answer_list = []

    question_text = await nodriver_get_text_by_selector(tab, question_selector, 'innerText')
    if len(question_text) > 0:
        write_question_to_file(question_text)

        answer_list = util.get_answer_list_from_user_guess_string(config_dict, CONST_MAXBOT_ANSWER_ONLINE_FILE)
        if len(answer_list)==0:
            if config_dict["advanced"]["auto_guess_options"]:
                answer_list = util.guess_tixcraft_question(driver, question_text)

        inferred_answer_string = ""
        for answer_item in answer_list:
            if not answer_item in fail_list:
                inferred_answer_string = answer_item
                break

        if show_debug_message:
            print("inferred_answer_string:", inferred_answer_string)
            print("answer_list:", answer_list)

        # PS: auto-focus() when empty inferred_answer_string with empty inputed text value.
        input_text_css = "input[name='checkCode']"
        next_step_button_css = ""
        submit_by_enter = True
        check_input_interval = 0.2
        is_answer_sent, fail_list = fill_common_verify_form(driver, config_dict, inferred_answer_string, fail_list, input_text_css, next_step_button_css, submit_by_enter, check_input_interval)

    return fail_list

async def nodriver_tixcraft_ticket_main(tab, config_dict, ocr, Captcha_Browser, domain_name):
    await nodriver_check_checkbox(tab, '#TicketForm_agree:not(:checked)')

async def nodirver_tixcraft_verify(tab, config_dict, fail_list):
    question_selector = '.zone-verify'
    return await nodriver_tixcraft_input_check_code(tab, config_dict, fail_list, question_selector)

async def nodriver_tixcraft_input_check_code(tab, config_dict, fail_list, question_selector):
    answer_list = []
    question_text = ""
    # TODO:
    '''
    question_text = get_text_by_selector(tab, question_selector, 'innerText')
    if len(question_text) > 0:
        write_question_to_file(question_text)

        answer_list = util.get_answer_list_from_user_guess_string(config_dict, CONST_MAXBOT_ANSWER_ONLINE_FILE)
        if len(answer_list)==0:
            if config_dict["advanced"]["auto_guess_options"]:
                answer_list = util.guess_tixcraft_question(tab, question_text)

        inferred_answer_string = ""
        for answer_item in answer_list:
            if not answer_item in fail_list:
                inferred_answer_string = answer_item
                break

        # PS: auto-focus() when empty inferred_answer_string with empty inputed text value.
        input_text_css = "input[name='checkCode']"
        next_step_button_css = ""
        submit_by_enter = True
        check_input_interval = 0.2
        is_answer_sent, fail_list = fill_common_verify_form(tab, config_dict, inferred_answer_string, fail_list, input_text_css, next_step_button_css, submit_by_enter, check_input_interval)
    '''
    return fail_list

async def nodriver_tixcraft_main(tab, url, config_dict, ocr, Captcha_Browser):
    global tixcraft_dict
    if not 'tixcraft_dict' in globals():
        tixcraft_dict = {}
        tixcraft_dict["fail_list"]=[]
        tixcraft_dict["fail_promo_list"]=[]
        tixcraft_dict["start_time"]=None
        tixcraft_dict["done_time"]=None
        tixcraft_dict["elapsed_time"]=None
        tixcraft_dict["is_popup_checkout"] = False
        tixcraft_dict["area_retry_count"]=0
        tixcraft_dict["played_sound_ticket"] = False
        tixcraft_dict["played_sound_order"] = False

    await nodriver_tixcraft_home_close_window(tab)

    # for event soldout or abnormal, url should redirect to user's homepage.
    if 'https://tixcraft.com/' == url or 'https://tixcraft.com/activity' == url:
        if "/activity/game/" in config_dict["homepage"] or "/activity/detail/" in config_dict["homepage"]:
            try:
                await tab.get(config_dict["homepage"])
            except Exception as e:
                pass

    if "/activity/detail/" in url:
        tixcraft_dict["start_time"] = time.time()
        is_redirected = await nodriver_tixcraft_redirect(tab, url)

    is_date_selected = False
    if "/activity/game/" in url:
        tixcraft_dict["start_time"] = time.time()
        if config_dict["date_auto_select"]["enable"]:
            domain_name = url.split('/')[2]
            # TODO:
            #is_date_selected = tixcraft_date_auto_select(driver, url, config_dict, domain_name)
            pass

    if '/artist/' in url and 'ticketmaster.com' in url:
        tixcraft_dict["start_time"] = time.time()
        if len(url.split('/'))==6:
            if config_dict["date_auto_select"]["enable"]:
                domain_name = url.split('/')[2]
                # TODO:
                #is_date_selected = ticketmaster_date_auto_select(driver, url, config_dict, domain_name)
                pass

    # choose area
    if '/ticket/area/' in url:
        domain_name = url.split('/')[2]
        if config_dict["area_auto_select"]["enable"]:
            if not 'ticketmaster' in domain_name:
                # for tixcraft
                # TODO:
                #tixcraft_area_auto_select(driver, url, config_dict)
                pass

                tixcraft_dict["area_retry_count"]+=1
                #print("count:", tixcraft_dict["area_retry_count"])
                if tixcraft_dict["area_retry_count"] >= (60 * 15):
                    # Cool-down
                    tixcraft_dict["area_retry_count"] = 0
                    time.sleep(5)
            else:
                # area auto select is too difficult, skip in this version.
                # TODO:
                #tixcraft_dict["fail_promo_list"] = ticketmaster_promo(driver, config_dict, tixcraft_dict["fail_promo_list"])
                #ticketmaster_assign_ticket_number(driver, config_dict)
                pass
    else:
        tixcraft_dict["fail_promo_list"] = []
        tixcraft_dict["area_retry_count"]=0

    # https://ticketmaster.sg/ticket/check-captcha/23_blackpink/954/5/75
    if '/ticket/check-captcha/' in url:
        domain_name = url.split('/')[2]
        # TODO:
        #ticketmaster_captcha(driver, config_dict, ocr, Captcha_Browser, domain_name)
        pass

    if '/ticket/verify/' in url:
        # TODO:
        #tixcraft_dict["fail_list"] = tixcraft_verify(driver, config_dict, tixcraft_dict["fail_list"])
        #tixcraft_dict["fail_list"] = await nodirver_tixcraft_verify(tab, config_dict, tixcraft_dict["fail_list"])
        pass
    else:
        tixcraft_dict["fail_list"] = []

    # main app, to select ticket number.
    if '/ticket/ticket/' in url:
        domain_name = url.split('/')[2]
        await nodriver_tixcraft_ticket_main(tab, config_dict, ocr, Captcha_Browser, domain_name)
        tixcraft_dict["done_time"] = time.time()

        if config_dict["advanced"]["play_sound"]["ticket"]:
            if not tixcraft_dict["played_sound_ticket"]:
                play_sound_while_ordering(config_dict)
            tixcraft_dict["played_sound_ticket"] = True

        tixcraft_dict["last_sent_minute"] = util.optimized_email_sending(config_dict, "ticket", tixcraft_dict["last_sent_minute"], url)
    else:
        tixcraft_dict["played_sound_ticket"] = False

    if '/ticket/order' in url:
        tixcraft_dict["done_time"] = time.time()

    is_quit_bot = False
    if '/ticket/checkout' in url:
        if not tixcraft_dict["start_time"] is None:
            if not tixcraft_dict["done_time"] is None:
                bot_elapsed_time = tixcraft_dict["done_time"] - tixcraft_dict["start_time"]
                if tixcraft_dict["elapsed_time"] != bot_elapsed_time:
                    print("bot elapsed time:", "{:.3f}".format(bot_elapsed_time))
                tixcraft_dict["elapsed_time"] = bot_elapsed_time

        if config_dict["advanced"]["headless"]:
            if not tixcraft_dict["is_popup_checkout"]:
                domain_name = url.split('/')[2]
                checkout_url = "https://%s/ticket/checkout" % (domain_name)
                print("搶票成功, 請前往該帳號訂單查看: %s" % (checkout_url))
                webbrowser.open_new(checkout_url)
                tixcraft_dict["is_popup_checkout"] = True
                is_quit_bot = True

        if config_dict["advanced"]["play_sound"]["order"]:
            if not tixcraft_dict["played_sound_order"]:
                play_sound_while_ordering(config_dict)
            tixcraft_dict["played_sound_order"] = True
        util.optimized_email_sending(config_dict, "order", None, url)
    else:
        tixcraft_dict["is_popup_checkout"] = False
        tixcraft_dict["played_sound_order"] = False

    return is_quit_bot

async def nodriver_ticketplus_account_sign_in(tab, config_dict):
    print("nodriver_ticketplus_account_sign_in")
    is_filled_form = False
    is_submited = False

    ticketplus_account = config_dict["advanced"]["ticketplus_account"]
    ticketplus_password = config_dict["advanced"]["ticketplus_password_plaintext"].strip()
    if ticketplus_password == "":
        ticketplus_password = util.decrypt_me(config_dict["advanced"]["ticketplus_password"])

    # manually keyin verify code.
    country_code = ""
    try:
        my_css_selector = 'input[placeholder="區碼"]'
        el_country = await tab.query_selector(my_css_selector)
        if el_country:
            country_code = await el_country.apply('function (element) { return element.value; } ')
            print("country_code", country_code)
    except Exception as exc:
        print(exc)

    is_account_assigned = False
    try:
        my_css_selector = 'input[placeholder="手機號碼 *"]'
        el_account = await tab.query_selector(my_css_selector)
        if el_account:
            await el_account.click()
            await el_account.apply('function (element) {element.value = ""; } ')
            await el_account.send_keys(ticketplus_account);
            is_account_assigned = True
    except Exception as exc:
        print(exc)

    if is_account_assigned:
        try:
            my_css_selector = 'input[type="password"]'
            el_password = await tab.query_selector(my_css_selector)
            if el_password:
                print("ticketplus_password:", ticketplus_password)
                await el_password.click()
                await el_password.apply('function (element) {element.value = ""; } ')
                await el_password.send_keys(ticketplus_password);
                time.sleep(0.1)
                is_filled_form = True

                if country_code=="+886":
                    # only this case to auto sumbmit.
                    print("press enter")
                    await tab.send(cdp.input_.dispatch_key_event("keyDown", code="Enter", key="Enter", text="\r", windows_virtual_key_code=13))
                    await tab.send(cdp.input_.dispatch_key_event("keyUp", code="Enter", key="Enter", text="\r", windows_virtual_key_code=13))
                    time.sleep(1)
                    # PS: ticketplus country field may not located at your target country.
                    is_submited = True
        except Exception as exc:
            print(exc)
            pass


    return is_filled_form, is_submited

async def nodriver_ticketplus_is_signin(tab):
    is_user_signin = False
    try:
        cookies  = await tab.browser.cookies.get_all()
        for cookie in cookies:
            if cookie.name=='user':
                if '%22account%22:%22' in cookie.value:
                    is_user_signin = True
        cookies = None
    except Exception as exc:
        print(exc)
        pass

    return is_user_signin


async def nodriver_ticketplus_account_auto_fill(tab, config_dict):
    global is_filled_ticketplus_singin_form

    if not 'is_filled_ticketplus_singin_form' in globals():
        is_filled_ticketplus_singin_form = False

    # auto fill account info.
    is_user_signin = False
    if len(config_dict["advanced"]["ticketplus_account"]) > 0:
        is_user_signin = await nodriver_ticketplus_is_signin(tab)
        print("is_user_signin:", is_user_signin)
        if not is_user_signin:
            time.sleep(0.1)
            if not is_filled_ticketplus_singin_form:
                is_sign_in_btn_pressed = False
                try:
                    # full screen mode.
                    my_css_selector = 'button.v-btn > span.v-btn__content > i.mdi-account'
                    sign_in_btn = await tab.query_selector(my_css_selector)
                    if sign_in_btn:
                        await sign_in_btn.click()
                        is_sign_in_btn_pressed = True
                        time.sleep(0.2)
                except Exception as exc:
                    print(exc)
                    pass

                #print("is_sign_in_btn_pressed", is_sign_in_btn_pressed)
                if not is_sign_in_btn_pressed:
                    #print("rwd mode")
                    action_btns = None
                    try:
                        my_css_selector = 'div.px-4.py-3.drawerItem.cursor-pointer'
                        action_btns = await tab.query_selector_all(my_css_selector)
                    except Exception as exc:
                        print(exc)
                        pass
                    if action_btns:
                        print("len:", len(action_btns))
                        if len(action_btns) >= 4:
                            try:
                                await action_btns[3].click()
                            except Exception as exc:
                                print(exc)
                                pass

                is_filled_form, is_submited = await nodriver_ticketplus_account_sign_in(tab, config_dict)
                if is_filled_form:
                    is_filled_ticketplus_singin_form = True

    return is_user_signin

async def nodriver_ticketplus_main(tab, url, config_dict, ocr, Captcha_Browser):
    global ticketplus_dict
    if not 'ticketplus_dict' in globals():
        ticketplus_dict = {}
        ticketplus_dict["fail_list"]=[]
        ticketplus_dict["is_popup_confirm"] = False

    home_url = 'https://ticketplus.com.tw/'
    is_user_signin = False
    if home_url == url.lower():
        if config_dict["ocr_captcha"]["enable"]:
            domain_name = url.split('/')[2]
            if not Captcha_Browser is None:
                # TODO:
                #Captcha_Browser.set_cookies(driver.get_cookies())
                Captcha_Browser.set_domain(domain_name)

        is_user_signin = await nodriver_ticketplus_account_auto_fill(tab, config_dict)

    if is_user_signin:
        # only sign in on homepage.
        if url != config_dict["homepage"]:
            try:
                await tab.get(config_dict["homepage"])
            except Exception as e:
                pass

    # https://ticketplus.com.tw/activity/XXX
    if '/activity/' in url.lower():
        is_event_page = False
        if len(url.split('/'))==5:
            is_event_page = True

        if is_event_page:
            # TODO:
            #is_button_pressed = ticketplus_accept_realname_card(driver)
            #print("is accept button pressed:", is_button_pressed)

            # TODO:
            #is_button_pressed = ticketplus_accept_other_activity(driver)
            #print("is accept button pressed:", is_button_pressed)

            if config_dict["date_auto_select"]["enable"]:
                # TODO:
                #ticketplus_date_auto_select(driver, config_dict)
                pass

    #https://ticketplus.com.tw/order/XXX/OOO
    if '/order/' in url.lower():
        is_event_page = False
        if len(url.split('/'))==6:
            is_event_page = True

        if is_event_page:
            # TODO:
            #is_button_pressed = ticketplus_accept_realname_card(driver)
            #is_button_pressed = ticketplus_accept_order_fail(driver)

            is_reloading = False

            is_reload_at_webdriver = False
            if not config_dict["browser"] in CONST_CHROME_FAMILY:
                is_reload_at_webdriver = True
            else:
                if not config_dict["advanced"]["chrome_extension"]:
                    is_reload_at_webdriver = True
            if is_reload_at_webdriver:
                # move below code to chrome extension.
                # TODO:
                #is_reloading = ticketplus_order_auto_reload_coming_soon(driver)
                pass

            if not is_reloading:
                # TODO:
                # is_captcha_sent, ticketplus_dict = ticketplus_order(driver, config_dict, ocr, Captcha_Browser, ticketplus_dict)
                pass

    else:
        ticketplus_dict["fail_list"]=[]

    #https://ticketplus.com.tw/confirm/xx/oo
    if '/confirm/' in url.lower() or '/confirmseat/' in url.lower():
        is_event_page = False
        if len(url.split('/'))==6:
            is_event_page = True

        if is_event_page:
            #print("is_popup_confirm",ticketplus_dict["is_popup_confirm"])
            if not ticketplus_dict["is_popup_confirm"]:
                ticketplus_dict["is_popup_confirm"] = True
                play_sound_while_ordering(config_dict)

            # TODO:
            #ticketplus_confirm(driver, config_dict)
        else:
            ticketplus_dict["is_popup_confirm"] = False
    else:
        ticketplus_dict["is_popup_confirm"] = False

async def nodriver_ibon_ticket_agree(tab):
    for i in range(3):
        is_finish_checkbox_click = await nodriver_check_checkbox(tab, '#agreen:not(:checked)')
        if is_finish_checkbox_click:
            break

async def nodriver_ibon_date_auto_select(tab, config_dict, date_keyword_item):
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    auto_select_mode = config_dict["date_auto_select"]["mode"]

    is_date_click_by_bot = False
    is_need_refresh = False
    is_tr_ready = False

    #data_list = []
    matched_blocks = []
    try:
        select_query = "#divGameInfo > app-game"
        div_host: Element = await tab.query_selector(select_query)
        if div_host:
            if div_host.shadow_roots:
                iframe: Node = div_host.shadow_roots[0]
                if iframe:
                    for lv1 in iframe.children:
                        if lv1.local_name=='div':
                            for lv2 in lv1.children:
                                if lv2.local_name=='div' and 'id' in lv2.attributes and 'GameInfoList' in lv2.attributes:
                                    for col_12 in lv2.children:
                                        if col_12.local_name=='div':
                                            is_tr_ready = True
                                            for d_flex in col_12.children:
                                                row_text = ""
                                                p_button = None
                                                p_index = -1
                                                for p in d_flex.children:
                                                    p_index += 1
                                                    if p.local_name == 'p':
                                                        p_text = ""
                                                        for text_node in p.children:
                                                            if text_node.node_name=='#text':
                                                                p_text += text_node.node_value

                                                            if p_index == 3:
                                                                if text_node.local_name=='button':
                                                                    if not 'disabled' in text_node.attributes:
                                                                        p_button = text_node
                                                        
                                                        if not p_text is None:
                                                            p_text = p_text.strip()
                                                            p_text = p_text.replace(",","")
                                                            p_text = p_text.upper()
                                                        row_text += p_text

                                                if p_button is None:
                                                    row_text = ""

                                                if len(row_text) > 0:
                                                    if util.reset_row_text_if_match_keyword_exclude(config_dict, row_text):
                                                        row_text = ""

                                                if len(row_text) > 0:
                                                    row_text = util.format_keyword_string(row_text)

                                                    is_match_area = False
                                                    if len(date_keyword_item) > 0:
                                                        # must match keyword.
                                                        is_match_area = True
                                                        date_keyword_array = date_keyword_item.split(' ')
                                                        for date_keyword in date_keyword_array:
                                                            date_keyword = util.format_keyword_string(date_keyword)
                                                            if not date_keyword in row_text:
                                                                is_match_area = False
                                                                break
                                                    else:
                                                        # without keyword.
                                                        is_match_area = True

                                                    if is_match_area:
                                                        matched_blocks.append(p_button)
    except Exception as exc:
        print(exc)
        pass

    if len(matched_blocks) > 0:
        matched_blocks_count = len(matched_blocks)
        if show_debug_message:
            print("matched_blocks count:", matched_blocks_count)

        target_area = util.get_target_item_from_matched_list(matched_blocks, auto_select_mode)
        if target_area:
            wrapper: Element = uc.core.element.create(target_area, tab)
            print("click on button")
            try:
                await wrapper.click()
                is_date_click_by_bot = True
            except Exception as exc:
                pass
    else:
        if is_tr_ready:
            is_need_refresh = True

    return is_need_refresh, is_date_click_by_bot

async def nodriver_ibon_area_auto_select(tab, config_dict, area_keyword_item):
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    auto_select_mode = config_dict["area_auto_select"]["mode"]

    is_price_assign_by_bot = False
    is_need_refresh = False
    is_tr_ready = False

    data_list = []
    try:
        select_query = "#AreaTable > div"
        div_host: Element = await tab.query_selector(select_query)
        if div_host:
            if div_host.shadow_roots:
                iframe: Node = div_host.shadow_roots[0]
                if iframe:
                    for node in iframe.children:
                        if node.local_name=='table':
                            for children in node.children:
                                if children.local_name=='tbody':
                                    for tr in children.children:
                                        if 'id' in tr.attributes and 'class' in tr.attributes:
                                            is_tr_ready = True

                                            skip_this_row = False
                                            if 'disabled' in tr.attributes:
                                                skip_this_row = True
                                            if 'sold-out' in tr.attributes:
                                                skip_this_row = True
                                            if not skip_this_row:
                                                data_list.append(tr)
    except Exception as exc:
        print(exc)
        pass

    matched_blocks = []
    if len(data_list) > 0:
        area_list_count = len(data_list)

        if show_debug_message:
            print("area_list_count:", area_list_count)
            print("area_keyword_item:", area_keyword_item)

        # filter list.
        for row in data_list:
            row_text = ""
            try:
                skip_this_row = False
                for td in row.children:
                    for text in td.children:
                        if text.local_name=="":
                            row_text += " " + text.node_value

                            if '已售完' == text.node_value:
                                skip_this_row = True
                            if '座位已被選擇' == text.node_value:
                                skip_this_row = True
                            if '座位已售出' == text.node_value:
                                skip_this_row = True
                            if '舞台區域' == text.node_value:
                                skip_this_row = True
                        if skip_this_row:
                            break
                    if skip_this_row:
                        break
                if skip_this_row:
                    row_text = ""
            except Exception as exc:
                print(exc)
                break

            if len(row_text) > 0:
                row_text = row_text.replace(",","")
                row_text = row_text.upper()

                if util.reset_row_text_if_match_keyword_exclude(config_dict, row_text):
                    row_text = ""

            if len(row_text) > 0:
                row_text = util.format_keyword_string(row_text)
                if show_debug_message:
                    print("row_text:", row_text)

                is_match_area = False

                if len(area_keyword_item) > 0:
                    # must match keyword.
                    is_match_area = True
                    area_keyword_array = area_keyword_item.split(' ')
                    for area_keyword in area_keyword_array:
                        area_keyword = util.format_keyword_string(area_keyword)
                        if not area_keyword in row_text:
                            is_match_area = False
                            break
                else:
                    # without keyword.
                    is_match_area = True

                if is_match_area:
                    matched_blocks.append(row)


    if len(matched_blocks) > 0:
        matched_blocks_count = len(matched_blocks)
        if show_debug_message:
            print("matched_blocks count:", matched_blocks_count)

        target_area = util.get_target_item_from_matched_list(matched_blocks, auto_select_mode)
        if target_area:
            wrapper: Element = uc.core.element.create(target_area, tab)
            print("click on tr")
            try:
                await wrapper.click()
                is_price_assign_by_bot = True
            except Exception as exc:
                pass
    else:
        if is_tr_ready:
            is_need_refresh = True

    return is_need_refresh, is_price_assign_by_bot

async def nodriver_ibon_activityinfo(tab, config_dict):
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    is_date_click_by_bot = False
    is_need_refresh = False

    # click price row.
    date_keyword = config_dict["date_auto_select"]["date_keyword"].strip()

    is_need_refresh = False

    if len(date_keyword) > 0:
        date_keyword_item = []
        try:
            date_keyword_item = json.loads("["+ date_keyword +"]")
        except Exception as exc:
            date_keyword_item = []

        for date_keyword_item in date_keyword_item:
            is_need_refresh, is_date_click_by_bot = await nodriver_ibon_date_auto_select(tab, config_dict, date_keyword_item)
            if not is_need_refresh:
                break
            else:
                print("is_need_refresh for keyword:", date_keyword_item)
    else:
        # empty keyword, match all.
        is_need_refresh, is_date_click_by_bot = await nodriver_ibon_date_auto_select(tab, config_dict, date_keyword)

    if show_debug_message:
        print("is_need_refresh:", is_need_refresh)

    if is_need_refresh:
        try:
            await tab.reload()
        except Exception as exc:
            pass

        if config_dict["advanced"]["auto_reload_page_interval"] > 0:
            time.sleep(config_dict["advanced"]["auto_reload_page_interval"])

    return is_date_click_by_bot

async def nodriver_ibon_performance(tab, config_dict):
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    is_price_assign_by_bot = False
    is_need_refresh = False

    # click price row.
    area_keyword = config_dict["area_auto_select"]["area_keyword"].strip()

    if len(area_keyword) > 0:
        area_keyword_array = []
        try:
            area_keyword_array = json.loads("["+ area_keyword +"]")
        except Exception as exc:
            area_keyword_array = []

        for area_keyword_item in area_keyword_array:
            is_need_refresh, is_price_assign_by_bot = await nodriver_ibon_area_auto_select(tab, config_dict, area_keyword_item)
            if not is_need_refresh:
                break
            else:
                print("is_need_refresh for keyword:", area_keyword_item)
    else:
        # empty keyword, match all.
        is_need_refresh, is_price_assign_by_bot = await nodriver_ibon_area_auto_select(tab, config_dict, area_keyword)

    if show_debug_message:
        print("is_need_refresh:", is_need_refresh)

    if is_need_refresh:
        try:
            await tab.reload()
        except Exception as exc:
            pass
        
        if config_dict["advanced"]["auto_reload_page_interval"] > 0:
            time.sleep(config_dict["advanced"]["auto_reload_page_interval"])


    return is_price_assign_by_bot

async def nodriver_ibon_next(tab, config_dict):
    try:
        select_query = "div#Next > div"
        div_host: Element = await tab.query_selector(select_query)
        if div_host:
            if div_host.shadow_roots:
                iframe: Node = div_host.shadow_roots[0]
                if iframe:
                    for node in iframe.children:
                        if node.local_name=='a':
                            a_tag: Element = uc.core.element.create(node, tab)
                            await a_tag.click()
    except Exception as exc:
        print(exc)
        pass

async def nodriver_ibon_ocr_span_shadow(tab, config_dict, ocr, node):
    try:
        img_tag: Element = uc.core.element.create(node, tab)
        if img_tag:
            #html = await img_tag.get_html()
            #print(html)
            img_data = await img_tag.apply("""function (img) {
let canvas = document.createElement('canvas');
let context = canvas.getContext('2d');
canvas.height = img.naturalHeight;
canvas.width = img.naturalWidth;
context.drawImage(img, 0, 0);
let img_data = canvas.toDataURL();
if(img_data) {image_data = img_data.split(",")[1];}
return img_data;
                            } """)
            ocr_answer = ""
            img_base64 = None
            if len(img_data) > 0:
                img_base64 = base64.b64decode(img_data.split(',')[1])
            if img_base64:
                ocr_answer = ocr.classification(img_base64)
            if len(ocr_answer) == 4:
                print(ocr_answer)
                select_query = "div.editor-box > div > input[type='text']"
                ocr_input: Element = await tab.query_selector(select_query)
                if ocr_input:
                    await ocr_input.click()
                    await ocr_input.apply('function (element) {element.value = ""}')
                    await ocr_input.send_keys(ocr_answer)
                    await nodriver_ibon_next(tab, config_dict)
            else:
                select_query = 'img[onclick="refreshCaptcha();"]'
                refresh_button: Element = await tab.query_selector(select_query)
                if refresh_button:
                    await refresh_button.click()
                    time.sleep(0.5)
    except Exception as exc:
        print(exc)
        pass

async def nodriver_ibon_ocr_span(tab, config_dict, ocr):
    try:
        select_query = "#ticket-wrap > div.row > div > div > div > span"
        div_host: Element = await tab.query_selector(select_query)
        if div_host:
            if div_host.shadow_roots:
                iframe: Node = div_host.shadow_roots[0]
                if iframe:
                    for node in iframe.children:
                        if node.local_name=='img':
                            await nodriver_ibon_ocr_span_shadow(tab, config_dict, ocr, node)
    except Exception as exc:
        print(exc)
        pass

async def nodriver_get_ibon_question_text(tab):
    question_text = ""
    if tab:
        try:
            select_query = "#content div[id] p"
            element = await tab.query_selector(select_query)
            if element:
                question_text = element.text
            else:
                #print("element not found:", select_query)
                pass
        except Exception as e:
            #print("click fail for selector:", select_query)
            print(e)
            pass
    return question_text

async def nodriver_fill_common_verify_form(tab, config_dict, inferred_answer_string, fail_list, input_text_css, next_step_button_css, submit_by_enter, check_input_interval):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    form_input_list = []
    try:
        form_input_list = await tab.query_selector_all(input_text_css)
    except Exception as exc:
        if show_debug_message:
            print("find verify code input textbox fail")
        pass
    if form_input_list is None:
        form_input_list = []

    form_input_count = len(form_input_list)
    if show_debug_message:
        print("input textbox count:", form_input_count)

    is_do_press_next_button = False

    form_input_1 = None
    form_input_2 = None
    if form_input_count > 0:
        form_input_1 = form_input_list[0]
        if form_input_count > 1:
            form_input_2 = form_input_list[1]

    is_multi_question_mode = False
    answer_list = util.get_answer_list_from_user_guess_string(config_dict, CONST_MAXBOT_ANSWER_ONLINE_FILE)
    if form_input_count == 1:
        is_do_press_next_button = True
    else:
        if form_input_count == 2:
            if not form_input_2 is None:
                if len(answer_list) >= 2:
                    if(len(answer_list[0]) > 0):
                        if(len(answer_list[1]) > 0):
                            is_multi_question_mode = True

    inputed_value_1 = None
    if not form_input_1 is None:
        try:
            inputed_value_1 = await form_input_1.apply("(el) => el.value")
        except Exception as exc:
            if show_debug_message:
                print("get_attribute of verify code fail")
            pass
    if inputed_value_1 is None:
        inputed_value_1 = ""

    inputed_value_2 = None
    if not form_input_2 is None:
        try:
            inputed_value_2 = await form_input_2.apply("(el) => el.value")
        except Exception as exc:
            if show_debug_message:
                print("get_attribute of verify code fail")
            pass
    if inputed_value_2 is None:
        inputed_value_2 = ""

    is_answer_sent = False
    if not is_multi_question_mode:
        if not form_input_1 is None:
            if len(inferred_answer_string) > 0:
                if inputed_value_1 != inferred_answer_string:
                    try:
                        # PS: sometime may send key twice...
                        await form_input_1.click()
                        await form_input_1.apply('function (element) {element.value = ""; } ')
                        await form_input_1.send_keys(inferred_answer_string);
                    except Exception as exc:
                        if show_debug_message:
                            print(exc)
                        pass

                is_button_clicked = False
                try:
                    if is_do_press_next_button:
                        if len(next_step_button_css) > 0:
                            is_button_clicked = await nodriver_press_button(tab, next_step_button_css)
                except Exception as exc:
                    if show_debug_message:
                        print(exc)
                    pass

                if is_button_clicked:
                    is_answer_sent = True
                    fail_list.append(inferred_answer_string)
                    if show_debug_message:
                        print("sent password by bot:", inferred_answer_string, " at #", len(fail_list))

                if is_answer_sent:
                    for i in range(3):
                        time.sleep(0.1)
                        alert_ret = False
                        #alert_ret = check_pop_alert(driver)
                        if alert_ret:
                            if show_debug_message:
                                print("press accept button at time #", i+1)
                            break
            else:
                # no answer to fill.
                pass

    else:
        # multi question mode.
        try:
            if inputed_value_1 != answer_list[0]:
                await form_input_1.click()
                await form_input_1.apply('function (element) {element.value = ""; } ')
                await form_input_1.send_keys(answer_list[0]);

            if inputed_value_2 != answer_list[1]:
                await form_input_2.click()
                await form_input_2.apply('function (element) {element.value = ""; } ')
                await form_input_2.send_keys(answer_list[1]);
            
            is_button_clicked = False
            is_button_clicked = await nodriver_press_button(tab, next_step_button_css)

            if is_button_clicked:
                is_answer_sent = True
                fail_list.append(answer_list[0])
                fail_list.append(answer_list[1])
                if show_debug_message:
                    print("sent password by bot:", inferred_answer_string, " at #", len(fail_list))
        except Exception as exc:
            pass

    return is_answer_sent, fail_list

async def nodriver_ibon_verification_question(tab, fail_list, config_dict):
    show_debug_message = False      # online

    if config_dict["advanced"]["verbose"]:
        show_debug_message = True

    answer_list = []

    question_text = await nodriver_get_ibon_question_text(tab)
    if len(question_text) > 0:
        js="window.alert = function() {}; window.confirm = function() { return true; }; window.prompt = function() { return null; };"
        await tab.evaluate(js)
        write_question_to_file(question_text)

        answer_list = util.get_answer_list_from_user_guess_string(config_dict, CONST_MAXBOT_ANSWER_ONLINE_FILE)
        if len(answer_list)==0:
            if config_dict["advanced"]["auto_guess_options"]:
                answer_list = util.get_answer_list_from_question_string(None, question_text)

        inferred_answer_string = ""
        if len(answer_list) > 0:
            for answer_item in answer_list:
                if not answer_item in fail_list:
                    inferred_answer_string = answer_item
                    break

        if show_debug_message:
            print("inferred_answer_string:", inferred_answer_string)
            print("answer_list:", answer_list)
            print("fail_list:", fail_list)

        # PS: auto-focus() when empty inferred_answer_string with empty inputed text value.
        input_text_css = '#content div.editor-box input'
        next_step_button_css = '#content div.editor-box a.btn'
        submit_by_enter = False
        check_input_interval = 0.2
        is_answer_sent, fail_list = await nodriver_fill_common_verify_form(tab, config_dict, inferred_answer_string, fail_list, input_text_css, next_step_button_css, submit_by_enter, check_input_interval)

    return fail_list

async def nodriver_ibon_main(tab, url, config_dict, ocr, Captcha_Browser):
    global ibon_dict
    if not 'ibon_dict' in globals():
        ibon_dict = {}
        ibon_dict["fail_list"]=[]
        ibon_dict["start_time"]=None
        ibon_dict["done_time"]=None
        ibon_dict["elapsed_time"]=None
        ibon_dict["last_sent_minute"]=None

    home_url_list = ['https://ticket.ibon.com.tw/'
    ,'https://ticket.ibon.com.tw/index/entertainment'
    ]
    for each_url in home_url_list:
        if each_url == url.lower():
            if config_dict["ocr_captcha"]["enable"]:
                # TODO:
                #set_non_browser_cookies(driver, url, Captcha_Browser)
                pass
            break

    # https://tour.ibon.com.tw/event/e23010000300mxu
    if 'tour' in url.lower() and '/event/' in url.lower():
        is_event_page = False
        if len(url.split('/'))==5:
            is_event_page = True
        if is_event_page:
            # ibon auto press signup
            try:
                await nodriver_press_button(tab, '.btn.btn-signup')
            except Exception as exc:
                print(exc)
                pass

    is_match_target_feature = False

    #PS: ibon some utk is upper case, some is lower.
    if not is_match_target_feature:
        #https://ticket.ibon.com.tw/ActivityInfo/Details/0000?pattern=entertainment
        if '/activityinfo/details/' in url.lower():
            is_event_page = False
            if len(url.split('/'))==6:
                is_event_page = True

            if is_event_page:
                if config_dict["date_auto_select"]["enable"]:
                    is_match_target_feature = True
                    is_date_click_by_bot = await nodriver_ibon_activityinfo(tab, config_dict)
                    pass

    if 'ibon.com.tw/error.html?' in url.lower():
        try:
            await tab.back()
        except Exception as exc:
            pass

    is_enter_verify_mode = False
    if not is_match_target_feature:
        # validation question url:
        # https://orders.ibon.com.tw/application/UTK02/UTK0201_0.aspx?rn=1180872370&PERFORMANCE_ID=B04M7XZT&PRODUCT_ID=B04KS88E&SHOW_PLACE_MAP=True
        is_event_page = False
        if '/UTK02/UTK0201_0.' in url.upper():
            if '.aspx?' in url.lower():
                if 'rn=' in url.lower():
                    if 'PERFORMANCE_ID=' in url.upper():
                        if "PRODUCT_ID=" in url.upper():
                            is_event_page = True

        if is_event_page:
            is_enter_verify_mode = True
            ibon_dict["fail_list"] = await nodriver_ibon_verification_question(tab, ibon_dict["fail_list"], config_dict)
            pass
            is_match_target_feature = True

    if not is_enter_verify_mode:
        ibon_dict["fail_list"] = []

    if not is_match_target_feature:
        # https://orders.ibon.com.tw/application/UTK02/UTK0201_000.aspx?PERFORMANCE_ID=0000
        # https://orders.ibon.com.tw/application/UTK02/UTK0201_000.aspx?rn=1111&PERFORMANCE_ID=2222&PRODUCT_ID=BBBB
        # https://orders.ibon.com.tw/application/UTK02/UTK0201_001.aspx?PERFORMANCE_ID=2222&GROUP_ID=4&PERFORMANCE_PRICE_AREA_ID=3333

        is_event_page = False
        if '/UTK02/UTK0201_' in url.upper():
            if '.aspx?' in url.lower():
                if 'PERFORMANCE_ID=' in url.upper():
                    if len(url.split('/'))==6:
                        is_event_page = True

        if '/UTK02/UTK0202_' in url.upper():
            if '.aspx?' in url.lower():
                if 'PERFORMANCE_ID=' in url.upper():
                    if len(url.split('/'))==6:
                        is_event_page = True

        if '/UTK02/UTK0204_' in url.upper():
            if '.aspx?' in url.lower():
                if 'PERFORMANCE_ID=' in url.upper():
                    if len(url.split('/'))==6:
                        is_event_page = True

        if is_event_page:
            if config_dict["area_auto_select"]["enable"]:
                if 'PRODUCT_ID=' in url.upper():
                    is_price_assign_by_bot = await nodriver_ibon_performance(tab, config_dict)

                if 'PERFORMANCE_PRICE_AREA_ID=' in url.upper():
                    if config_dict["advanced"]["disable_adjacent_seat"]:
                        # solution 1:
                        #is_finish_checkbox_click = await nodriver_check_checkbox(tab, '.asp-checkbox > input[type="checkbox"]:not(:checked)')
                        # solution 2:
                        js = """
$('input[type=checkbox]').each(function() {
   $(this).prop('checked', true);
});"""
                        try:
                            await tab.evaluate(js)
                        except Exception as exc:
                            print(exc)
                            pass

                    if config_dict["ticket_number"] > 0:
                        js = """
var ticket_number = {};
var $main_table = $("table.table");
if ($main_table.length > 0){{
    var $ticket_options = $main_table.find("select:first option");
    if ($ticket_options.length){{
        var is_ticket_number_assign = false;
        $ticket_options.each(function () {{
            if ($(this).val() == ticket_number) {{
                $(this).prop('selected', true);
                is_ticket_number_assign = true;
                return false;
            }}
        }});
        if (!is_ticket_number_assign) $ticket_options.last().prop('selected', true);
    }} else history.back();
}}""".format(config_dict["ticket_number"])
                        try:
                            await tab.evaluate(js)
                        except Exception as exc:
                            print(exc)
                            pass

                        try:
                            select_query = "table.table select"
                            ticket_select: Element = await tab.query_selector(select_query)
                            if ticket_select:
                                selected_ticket_value = 0
                                selected_ticket_string = await ticket_select.apply("(el) => el.value")
                                if selected_ticket_string:
                                    if len(selected_ticket_string) > 0:
                                        selected_ticket_value = int(selected_ticket_string)

                                if selected_ticket_value > 0:
                                    await nodriver_ibon_ocr_span(tab, config_dict, ocr)
                        except Exception as exc:
                            print(exc)
                            pass


    if not is_match_target_feature:
        #https://orders.ibon.com.tw/application/UTK02/UTK0206_.aspx
        is_event_page = False
        if '/UTK02/UTK020' in url.upper():
            if '.aspx' in url.lower():
                if len(url.split('/'))==6:
                    is_event_page = True

        # ignore "pay money" step.
        if '/UTK02/UTK0207_.ASPX' in url.upper():
            is_event_page = False

        if is_event_page:
            if is_event_page:
                is_match_target_feature = True
                is_finish_checkbox_click = await nodriver_ibon_ticket_agree(tab)
                if is_finish_checkbox_click:
                    is_name_based = False
                    try:
                        html_body = await tab.get_content()
                        #print("html_body:",len(html_body))
                        if html_body:
                            if len(html_body) > 1024:
                                if '實名制' in html_body:
                                    is_name_based = True
                    except Exception as exc:
                        #print(exc)
                        pass

                    if not is_name_based:
                        is_button_clicked = await nodriver_press_button(tab, 'a.btn.btn-pink.continue')
                        
                    if config_dict["advanced"]["play_sound"]["ticket"]:
                        if not played_sound_ticket:
                            play_sound_while_ordering(config_dict)
                        played_sound_ticket = True

                    ibon_dict["last_sent_minute"] = util.optimized_email_sending(config_dict, "ticket", ibon_dict["last_sent_minute"], url)


async def nodriver_cityline_auto_retry_access(tab, url, config_dict):
    try:
        js = "goEvent();"
        await tab.evaluate(js)
    except Exception as exc:
        print(exc)
        pass

    # 刷太快, 會被封IP?
    # must wait...? no need to wait.
    auto_reload_page_interval = config_dict["advanced"]["auto_reload_page_interval"]
    if auto_reload_page_interval > 0:
        time.sleep(auto_reload_page_interval)

async def nodriver_cityline_login(tab, cityline_account):
    global is_cityline_account_assigned
    if not 'is_cityline_account_assigned' in globals():
        is_cityline_account_assigned = False

    #print("is_cityline_account_assigned", is_cityline_account_assigned)
    if not is_cityline_account_assigned:
        try:
            #await tab.verify_cf()
            el_account = await tab.query_selector('input[type="text"]')
            if el_account:
                await el_account.click()
                await el_account.apply('function (element) {element.value = ""; } ')
                await el_account.send_keys(cityline_account);
                time.sleep(0.5)
                is_cityline_account_assigned = True
        except Exception as exc:
            print(exc)
            pass
    else:
        # after account inputed.
        try:
            #is_checkbox_checked = await nodriver_check_checkbox(tab, 'span.ant-checkbox input[type="checkbox"]')
            #print("is_checkbox_checked", is_checkbox_checked)
            # jquery solution.
            #js="$('input:checkbox').prop('checked', true);"
            # javascript solution.
            #js = "for (const checkbox of document.querySelectorAll('input[type=checkbox]:not(:checked)')) { checkbox.checked = true;}"
            #await tab.evaluate(js)
            checkbox_readed = await tab.query_selector('input[type=checkbox]:not(:checked)')
            if checkbox_readed:
                print("click on readed.")
                await checkbox_readed.click()
            time.sleep(0.5)
        except Exception as exc:
            print(exc)
            pass

async def nodriver_cityline_date_auto_select(tab, auto_select_mode, date_keyword):
    show_debug_message = True       # debug.
    show_debug_message = False      # online

    ret = False

    area_list = None
    try:
        my_css_selector = "button.date-time-position"
        area_list = await tab.query_selector_all(my_css_selector)
    except Exception as exc:
        #print(exc)
        pass

    matched_blocks = None
    if area_list:
        formated_area_list = None
        area_list_count = len(area_list)
        if show_debug_message:
            print("date_list_count:", area_list_count)

        if area_list_count > 0:
            formated_area_list = area_list
            if show_debug_message:
                print("formated_area_list count:", len(formated_area_list))

            if len(date_keyword) == 0:
                matched_blocks = formated_area_list
            else:
                # match keyword.
                if show_debug_message:
                    print("start to match keyword:", date_keyword)
                matched_blocks = []

                for row in formated_area_list:
                    row_text = ""
                    row_html = ""
                    try:
                        row_html = await row.get_html()
                        row_text = util.remove_html_tags(row_html)
                        # PS: get_js_attributes on cityline due to: the JSON object must be str, bytes or bytearray, not NoneType
                        #js_attr = await row.get_js_attributes()
                        #row_html = js_attr["innerHTML"]
                        #row_text = js_attr["innerText"]
                    except Exception as exc:
                        if show_debug_message:
                            print(exc)
                        # error, exit loop
                        break

                    if len(row_text) > 0:
                        if show_debug_message:
                            print("row_text:", row_text)
                        is_match_area = util.is_row_match_keyword(date_keyword, row_text)
                        if is_match_area:
                            matched_blocks.append(row)
                            if auto_select_mode == CONST_FROM_TOP_TO_BOTTOM:
                                break

                if show_debug_message:
                    if not matched_blocks is None:
                        print("after match keyword, found count:", len(matched_blocks))
        else:
            print("not found date-time-position")
            pass
    else:
        #print("date date-time-position is None")
        pass

    target_area = util.get_target_item_from_matched_list(matched_blocks, auto_select_mode)
    if not target_area is None:
        try:
            await target_area.scroll_into_view()
            await target_area.click()
            ret = True
        except Exception as exc:
            print(exc)

    return ret

async def nodriver_check_modal_dialog_popup(tab):
    ret = False
    try:
        el_div = tab.query_selector('div.modal-dialog > div.modal-content')
        if el_div:
            ret = True
    except Exception as exc:
        print(exc)
        pass
    return ret

async def nodriver_cityline_purchase_button_press(tab, config_dict):
    date_auto_select_mode = config_dict["date_auto_select"]["mode"]
    date_keyword = config_dict["date_auto_select"]["date_keyword"].strip()
    is_date_assign_by_bot = await nodriver_cityline_date_auto_select(tab, date_auto_select_mode, date_keyword)

    is_button_clicked = False
    if is_date_assign_by_bot:
        print("press purchase button")
        await nodriver_press_button(tab, 'div.ticketCard > button.purchase-btn')
        is_button_clicked = True
        # wait reCAPTCHA popup.
        time.sleep(6)

    return is_button_clicked

async def nodriver_get_http_tab(driver):
    tabs = []
    driver_info = await driver._get_targets()
    await driver
    try:
        for i, each_tab in enumerate(driver):
            target_info = each_tab.target.to_json()
            target_url = ""
            if target_info:
                if "url" in target_info:
                    target_url = target_info["url"]
            if len(target_url) > 4:
                if target_url[:4]=="http" or target_url == "about:blank":
                    tabs.append(each_tab)
    except Exception as exc:
        print(exc)
        pass
    return tabs

async def nodriver_cityline_close_tab(tabs):
    if len(tabs) > 1:
        tmp_tab = tabs[0]
        try:
            html = await tmp_tab.get_content()
            #print("get_content:", html)
            if len(html) > 0:
                await tmp_tab.activate()
                await tmp_tab.close()
        except Exception as exc:
            pass

async def nodriver_cityline_close_second_tab(driver, current_tab, url):
    tabs = await nodriver_get_http_tab(driver)
    tab_count = len(tabs)
    #print("close_second_tab tab count:", tab_count)
    if tab_count > 1:
        # wait page ready.
        time.sleep(0.3)
        await nodriver_cityline_close_tab(tabs)
        time.sleep(0.3)
    return current_tab

async def nodriver_cityline_main(driver, tab, url, config_dict):
    global cityline_dict
    if not 'cityline_dict' in globals():
        cityline_dict = {}
        cityline_dict["played_sound_ticket"] = False

    if 'msg.cityline.com' in url or 'event.cityline.com' in url:
        is_dom_ready = False
        try:
            html_body = await tab.get_content()
            if html_body:
                if len(html_body) > 1024:
                    is_dom_ready = True
        except Exception as exc:
            pass
        if is_dom_ready:
            #await nodriver_cityline_auto_retry_access(tab, url, config_dict)
            pass

    if 'cityline.com/Login.html' in url:
        cityline_account = config_dict["advanced"]["cityline_account"]
        if len(cityline_account) > 4:
            await nodriver_cityline_login(tab, cityline_account)

    tab = await nodriver_cityline_close_second_tab(driver, tab, url)

    # date page.
    #https://venue.cityline.com/utsvInternet/EVENT_NAME/eventDetail?event=EVENT_CODE
    global cityline_purchase_button_pressed
    if not 'cityline_purchase_button_pressed' in globals():
        cityline_purchase_button_pressed = False
    if '/eventDetail?' in url:
        # detect fail.
        #is_modal_dialog_popup = await nodriver_check_modal_dialog_popup(tab)

        if not cityline_purchase_button_pressed:
            if config_dict["date_auto_select"]["enable"]:
                is_button_clicked = await nodriver_cityline_purchase_button_press(tab, config_dict)
                if is_button_clicked:
                    cityline_purchase_button_pressed = True
    else:
        cityline_purchase_button_pressed = False


    # area page:
    # TODO:
    #https://venue.cityline.com/utsvInternet/EVENT_NAME/performance?event=EVENT_CODE&perfId=PROFORMANCE_ID
    if 'venue.cityline.com' in url and '/performance?':
        if config_dict["advanced"]["play_sound"]["ticket"]:
            if not cityline_dict["played_sound_ticket"]:
                play_sound_while_ordering(config_dict)
            cityline_dict["played_sound_ticket"] = True
    else:
        cityline_dict["played_sound_ticket"] = False

    return tab

async def nodriver_facebook_main(tab, config_dict):
    facebook_account = config_dict["advanced"]["facebook_account"].strip()
    facebook_password = config_dict["advanced"]["facebook_password_plaintext"].strip()
    if facebook_password == "":
        facebook_password = util.decrypt_me(config_dict["advanced"]["facebook_password"])
    if len(facebook_account) > 4:
        await nodriver_facebook_login(tab, facebook_account, facebook_password)

def get_nodriver_browser_args():
    browser_args = [
        "--disable-animations",
        "--disable-app-info-dialog-mac",
        "--disable-background-networking",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-dev-shm-usage",
        "--disable-device-discovery-notifications",
        "--disable-dinosaur-easter-egg",
        "--disable-domain-reliability",
        "--disable-features=IsolateOrigins,site-per-process,TranslateUI",
        "--disable-infobars",
        "--disable-logging",
        "--disable-login-animations",
        "--disable-login-screen-apps",
        "--disable-notifications",
        "--disable-password-generation",
        "--disable-popup-blocking",
        "--disable-renderer-backgrounding",
        "--disable-session-crashed-bubble",
        "--disable-smooth-scrolling",
        "--disable-suggestions-ui",
        "--disable-sync",
        "--disable-translate",
        "--hide-crash-restore-bubble",
        "--homepage=about:blank",
        "--no-default-browser-check",
        "--no-first-run",
        "--no-pings",
        "--no-service-autorun",
        "--password-store=basic",
        "--remote-debugging-host=127.0.0.1",
        #"--disable-remote-fonts",
    ]

    return browser_args

def get_maxbot_extension_path(extension_folder):
    app_root = util.get_app_root()
    extension_path = "webdriver"
    extension_path = os.path.join(extension_path, extension_folder)
    config_filepath = os.path.join(app_root, extension_path)
    #print("config_filepath:", config_filepath)

    # double check extesion mainfest
    path = pathlib.Path(config_filepath)
    if path.exists():
        if path.is_dir():
            #print("found extension dir")
            for item in path.rglob("manifest.*"):
                path = item.parent
            #print("final path:", path)
    return config_filepath

def get_extension_config(config_dict):
    no_sandbox=True
    browser_args = get_nodriver_browser_args()
    if len(config_dict["advanced"]["proxy_server_port"]) > 2:
        browser_args.append('--proxy-server=%s' % config_dict["advanced"]["proxy_server_port"])
    conf = Config(browser_args=browser_args, no_sandbox=no_sandbox, headless=config_dict["advanced"]["headless"])
    if config_dict["advanced"]["chrome_extension"]:
        ext = get_maxbot_extension_path(CONST_MAXBOT_EXTENSION_NAME)
        if len(ext) > 0:
            clone_ext = ext.replace(CONST_MAXBOT_EXTENSION_NAME, "tmp_" + CONST_MAXBOT_EXTENSION_NAME + "_" + config_dict["token"])
            if not os.path.exists(clone_ext):
                os.mkdir(clone_ext)
            util.copytree(ext, clone_ext)

            conf.add_extension(clone_ext)
            util.dump_settings_to_maxbot_plus_extension(clone_ext, config_dict, CONST_MAXBOT_CONFIG_FILE)
    return conf

async def nodrver_block_urls(tab, config_dict):
    NETWORK_BLOCKED_URLS = []

    if config_dict["advanced"]["adblock"]:
        NETWORK_BLOCKED_URLS = [
            '*.clarity.ms/*',
            '*.doubleclick.net/*',
            '*.lndata.com/*',
            '*.rollbar.com/*',
            '*.twitter.com/i/*',
            '*/adblock.js',
            '*/google_ad_block.js',
            '*anymind360.com/*',
            '*cdn.cookielaw.org/*',
            '*e2elog.fetnet.net*',
            '*fundingchoicesmessages.google.com/*',
            '*google-analytics.*',
            '*googlesyndication.*',
            '*googletagmanager.*',
            '*googletagservices.*',
            '*img.uniicreative.com/*',
            '*platform.twitter.com/*',
            '*play.google.com/*',
            '*player.youku.*',
            '*syndication.twitter.com/*',
            '*youtube.com/*',
        ]

    if config_dict["advanced"]["hide_some_image"]:
        NETWORK_BLOCKED_URLS.append('*.woff')
        NETWORK_BLOCKED_URLS.append('*.woff2')
        NETWORK_BLOCKED_URLS.append('*.ttf')
        NETWORK_BLOCKED_URLS.append('*.otf')
        NETWORK_BLOCKED_URLS.append('*fonts.googleapis.com/earlyaccess/*')
        NETWORK_BLOCKED_URLS.append('*/ajax/libs/font-awesome/*')
        NETWORK_BLOCKED_URLS.append('*.ico')
        NETWORK_BLOCKED_URLS.append('*ticketimg2.azureedge.net/image/ActivityImage/*')
        NETWORK_BLOCKED_URLS.append('*static.tixcraft.com/images/activity/*')
        NETWORK_BLOCKED_URLS.append('*static.ticketmaster.sg/images/activity/*')
        NETWORK_BLOCKED_URLS.append('*static.ticketmaster.com/images/activity/*')
        NETWORK_BLOCKED_URLS.append('*ticketimg2.azureedge.net/image/ActivityImage/ActivityImage_*')
        NETWORK_BLOCKED_URLS.append('*.azureedge.net/QWARE_TICKET//images/*')
        NETWORK_BLOCKED_URLS.append('*static.ticketplus.com.tw/event/*')

        #NETWORK_BLOCKED_URLS.append('https://kktix.cc/change_locale?locale=*')
        NETWORK_BLOCKED_URLS.append('https://t.kfs.io/assets/logo_*.png')
        NETWORK_BLOCKED_URLS.append('https://t.kfs.io/assets/icon-*.png')
        NETWORK_BLOCKED_URLS.append('https://t.kfs.io/upload_images/*.jpg')

    if config_dict["advanced"]["block_facebook_network"]:
        NETWORK_BLOCKED_URLS.append('*facebook.com/*')
        NETWORK_BLOCKED_URLS.append('*.fbcdn.net/*')

    await tab.send(cdp.network.enable())
    # set_blocked_ur_ls is author's typo..., waiting author to chagne.
    await tab.send(cdp.network.set_blocked_ur_ls(NETWORK_BLOCKED_URLS))
    return tab

async def nodriver_resize_window(driver, config_dict):
    window_size = config_dict["advanced"]["window_size"]
    #print("window_size", window_size)
    if len(window_size) > 0:
        if "," in window_size:
            print("start to resize window")
            launch_counter = 1
            target_left = 0
            target_top = 30
            target_width = 480
            target_height = 1024
            size_array = window_size.split(",")
            if len(size_array) >= 2:
                target_width = int(size_array[0])
                target_height = int(size_array[1])
            if len(size_array) >= 3:
                if len(size_array[2]) > 0:
                    launch_counter = int(size_array[2])
                target_left = target_width * launch_counter
                if target_left >= 1440:
                    target_left = 0
            #tab = await driver.main_tab()
            try:
                for i, tab in enumerate(driver):
                    await tab.set_window_size(left=target_left, top=target_top, width=target_width, height=target_height)
            except Exception as exc:
                # cannot unpack non-iterable NoneType object
                print(exc)
                #print("請關閉所有視窗後，重新操作一次")
                pass

# we only handle last tab.
async def nodriver_current_url(driver, tab):
    exit_bot_error_strings = [
        "server rejected WebSocket connection: HTTP 500",
        "[Errno 61] Connect call failed ('127.0.0.1',",
        "[WinError 1225] ",
    ]
    # return value
    url = ""
    is_quit_bot = False
    last_active_tab = None

    driver_info = await driver._get_targets()
    if not tab.target in driver_info:
        print("tab may closed by user before, or popup confirm dialog.")
        tab = None
        await driver
        try:
            for i, each_tab in enumerate(driver):
                target_info = each_tab.target.to_json()
                target_url = ""
                if target_info:
                    if "url" in target_info:
                        target_url = target_info["url"]
                if len(target_url) > 4:
                    if target_url[:4]=="http" or target_url == "about:blank":
                        print("found tab url:", target_url)
                        last_active_tab = each_tab
        except Exception as exc:
            print(exc)
            if str(exc) == "list index out of range":
                print("Browser closed, start to exit bot.")
                is_quit_bot = True
                tab = None
                last_active_tab = None

        if not last_active_tab is None:
            tab = last_active_tab

    if tab:
        try:
            target_info = tab.target.to_json()
            if target_info:
                if "url" in target_info:
                    url = target_info["url"]
            #url = await tab.evaluate('window.location.href')
        except Exception as exc:
            print(exc)
            str_exc = ""
            try:
                str_exc = str(exc)
            except Exception as exc2:
                pass
            if len(str_exc) > 0:
                if str_exc == "server rejected WebSocket connection: HTTP 404":
                    print("目前 nodriver 還沒準備好..., 請等到沒出現這行訊息再開始使用。")

                for each_error_string in exit_bot_error_strings:
                    if each_error_string in str_exc:
                        #print('quit bot by error:', each_error_string, driver)
                        is_quit_bot = True
    return url, is_quit_bot, last_active_tab

def nodriver_overwrite_prefs(conf):
    #print(conf.user_data_dir)
    prefs_filepath = os.path.join(conf.user_data_dir,"Default")
    if not os.path.exists(prefs_filepath):
        os.mkdir(prefs_filepath)
    prefs_filepath = os.path.join(prefs_filepath,"Preferences")

    prefs_dict = {
        "credentials_enable_service": False,
        "ack_existing_ntp_extensions": False,
        "translate":{"enabled": False}}
    prefs_dict["in_product_help"]={}
    prefs_dict["in_product_help"]["snoozed_feature"]={}
    prefs_dict["in_product_help"]["snoozed_feature"]["IPH_LiveCaption"]={}
    prefs_dict["in_product_help"]["snoozed_feature"]["IPH_LiveCaption"]["is_dismissed"]=True
    prefs_dict["in_product_help"]["snoozed_feature"]["IPH_LiveCaption"]["last_dismissed_by"]=4
    prefs_dict["media_router"]={}
    prefs_dict["media_router"]["show_cast_sessions_started_by_other_devices"]={}
    prefs_dict["media_router"]["show_cast_sessions_started_by_other_devices"]["enabled"]=False
    prefs_dict["net"]={}
    prefs_dict["net"]["network_prediction_options"]=3
    prefs_dict["privacy_guide"]={}
    prefs_dict["privacy_guide"]["viewed"]=True
    prefs_dict["privacy_sandbox"]={}
    prefs_dict["privacy_sandbox"]["first_party_sets_enabled"]=False
    prefs_dict["profile"]={}
    #prefs_dict["profile"]["cookie_controls_mode"]=1
    prefs_dict["profile"]["default_content_setting_values"]={}
    prefs_dict["profile"]["default_content_setting_values"]["notifications"]=2
    prefs_dict["profile"]["default_content_setting_values"]["sound"]=2
    prefs_dict["profile"]["name"]=CONST_APP_VERSION
    prefs_dict["profile"]["password_manager_enabled"]=False
    prefs_dict["safebrowsing"]={}
    prefs_dict["safebrowsing"]["enabled"]=False
    prefs_dict["safebrowsing"]["enhanced"]=False
    prefs_dict["sync"]={}
    prefs_dict["sync"]["autofill_wallet_import_enabled_migrated"]=False

    json_str = json.dumps(prefs_dict)
    with open(prefs_filepath, 'w') as outfile:
        outfile.write(json_str)

    state_filepath = os.path.join(conf.user_data_dir,"Local State")
    state_dict = {}
    state_dict["dns_over_https"]={}
    state_dict["dns_over_https"]["mode"]="off"
    json_str = json.dumps(state_dict)
    with open(state_filepath, 'w') as outfile:
        outfile.write(json_str)

async def check_refresh_datetime_occur(driver, target_time):
    is_refresh_datetime_sent = False
    if len(target_time) > 0:
        system_clock_data = datetime.now()
        current_time = system_clock_data.strftime('%H:%M:%S')
        if target_time == current_time:
            try:
                for tab in driver.tabs:
                    await tab.reload()
                    is_refresh_datetime_sent = True
                    print("send refresh at time:", current_time)
            except Exception as exc:
                print(exc)
                pass

    return is_refresh_datetime_sent

async def sendkey_to_browser(driver, config_dict, url):
    tmp_filepath = ""
    if "token" in config_dict:
        app_root = util.get_app_root()
        tmp_file = config_dict["token"] + "_sendkey.tmp"
        tmp_filepath = os.path.join(app_root, tmp_file)

    if os.path.exists(tmp_filepath):
        sendkey_dict = None
        try:
            with open(tmp_filepath) as json_data:
                sendkey_dict = json.load(json_data)
                print(sendkey_dict)
        except Exception as e:
            print("error on open file")
            print(e)
            pass

        if sendkey_dict:
            #print("nodriver start to sendkey")
            for each_tab in driver.tabs:
                all_command_done = await sendkey_to_browser_exist(each_tab, sendkey_dict, url)

                # must all command success to delete tmp file.
                if all_command_done:
                    try:
                        os.unlink(tmp_filepath)
                        #print("remove file:", tmp_filepath)
                    except Exception as e:
                        pass

async def sendkey_to_browser_exist(tab, sendkey_dict, url):
    all_command_done = True
    if "command" in sendkey_dict:
        for cmd_dict in sendkey_dict["command"]:
            #print("cmd_dict", cmd_dict)
            matched_location = True
            if "location" in cmd_dict:
                if cmd_dict["location"] != url:
                    matched_location = False

            if matched_location:
                if cmd_dict["type"] == "sendkey":
                    print("sendkey")
                    target_text = cmd_dict["text"]
                    try:
                        element = await tab.query_selector(cmd_dict["selector"])
                        if element:
                            await element.click()
                            await element.apply('function (element) {element.value = ""; } ')
                            await element.send_keys(target_text);
                        else:
                            #print("element not found:", select_query)
                            pass
                    except Exception as e:
                        all_command_done = False
                        #print("click fail for selector:", select_query)
                        print(e)
                        pass

                if cmd_dict["type"] == "click":
                    print("click")
                    try:
                        element = await tab.query_selector(cmd_dict["selector"])
                        if element:
                            await element.click()
                        else:
                            #print("element not found:", select_query)
                            pass
                    except Exception as e:
                        all_command_done = False
                        #print("click fail for selector:", select_query)
                        print(e)
                        pass
            time.sleep(0.05)
    return all_command_done

async def eval_to_browser(driver, config_dict, url):
    tmp_filepath = ""
    if "token" in config_dict:
        app_root = util.get_app_root()
        tmp_file = config_dict["token"] + "_eval.tmp"
        tmp_filepath = os.path.join(app_root, tmp_file)

    if os.path.exists(tmp_filepath):
        eval_dict = None
        try:
            with open(tmp_filepath) as json_data:
                eval_dict = json.load(json_data)
                print(eval_dict)
        except Exception as e:
            print("error on open file")
            print(e)
            pass

        if eval_dict:
            #print("nodriver start to eval")
            for each_tab in driver.tabs:
                all_command_done = await eval_to_browser_exist(each_tab, eval_dict, url)

                # must all command success to delete tmp file.
                if all_command_done:
                    try:
                        os.unlink(tmp_filepath)
                        #print("remove file:", tmp_filepath)
                    except Exception as e:
                        pass

async def eval_to_browser_exist(tab, eval_dict, url):
    all_command_done = True
    if "command" in eval_dict:
        for cmd_dict in eval_dict["command"]:
            #print("cmd_dict", cmd_dict)
            matched_location = True
            if "location" in cmd_dict:
                if cmd_dict["location"] != url:
                    matched_location = False

            if matched_location:
                if cmd_dict["type"] == "eval":
                    print("eval")
                    target_script = cmd_dict["script"]
                    try:
                        await tab.evaluate(target_script)
                    except Exception as e:
                        all_command_done = False
                        #print("click fail for selector:", select_query)
                        print(e)
                        pass

            time.sleep(0.05)
    return all_command_done

async def main(args):
    config_dict = get_config_dict(args)
    config_dict["token"] = util.get_token()

    driver = None
    tab = None
    if not config_dict is None:
        conf = get_extension_config(config_dict)
        nodriver_overwrite_prefs(conf)
        #driver = await uc.start(conf, headless=config_dict["advanced"]["headless"])
        driver = await uc.start(conf)
        if not driver is None:
            tab = driver.main_tab
            await tab.send(cdp.page.add_script_to_evaluate_on_new_document(source="""
                Element.prototype._as = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function (params) {
                    return this._as({mode: "open"})
                };"""))
            tab = await nodriver_goto_homepage(driver, config_dict)
            tab = await nodrver_block_urls(tab, config_dict)
            if not config_dict["advanced"]["headless"]:
                await nodriver_resize_window(driver, config_dict)
        else:
            print("無法使用nodriver，程式無法繼續工作")
            sys.exit()
    else:
        print("Load config error!")

    url = ""
    last_url = ""

    fami_dict = {}
    fami_dict["fail_list"] = []
    fami_dict["last_activity"]=""

    ticketplus_dict = {}
    ticketplus_dict["fail_list"]=[]
    ticketplus_dict["is_popup_confirm"] = False

    ocr = None
    Captcha_Browser = None
    try:
        if config_dict["ocr_captcha"]["enable"]:
            ocr = ddddocr.DdddOcr(show_ad=False, beta=config_dict["ocr_captcha"]["beta"])
            Captcha_Browser = NonBrowser()
            if len(config_dict["advanced"]["tixcraft_sid"]) > 1:
                #set_non_browser_cookies(driver, config_dict["homepage"], Captcha_Browser)
                pass
    except Exception as exc:
        print(exc)
        pass

    is_quit_bot = False
    is_refresh_datetime_sent = False

    while True:
        time.sleep(0.05)

        # pass if driver not loaded.
        if driver is None:
            print("nodriver not accessible!")
            break

        if not is_quit_bot:
            url, is_quit_bot, reset_act_tab = await nodriver_current_url(driver, tab)
            if not reset_act_tab is None:
                tab = reset_act_tab
            #print("act_tab url:", url)

        if is_quit_bot:
            print("start to quit bot...")
            try:
                await driver.stop()
                driver = None
            except Exception as e:
                pass
            break

        if url is None:
            continue
        else:
            if len(url) == 0:
                continue

        if not is_refresh_datetime_sent:
            is_refresh_datetime_sent = await check_refresh_datetime_occur(driver, config_dict["refresh_datetime"])

        is_maxbot_paused = False
        if os.path.exists(CONST_MAXBOT_INT28_FILE):
            is_maxbot_paused = True
        sync_status_to_extension(not is_maxbot_paused)

        if len(url) > 0 :
            if url != last_url:
                print(url)
                write_last_url_to_file(url)
                if is_maxbot_paused:
                    print("MAXBOT Paused.")
            last_url = url

        if is_maxbot_paused:
            if 'kktix.c' in url:
                await nodriver_kktix_paused_main(tab, url, config_dict)
            # sleep more when paused.
            time.sleep(0.1)
            continue

        await sendkey_to_browser(driver, config_dict, url)
        await eval_to_browser(driver, config_dict, url)

        # for kktix.cc and kktix.com
        if 'kktix.c' in url:
            is_quit_bot = await nodriver_kktix_main(tab, url, config_dict)
            pass

        tixcraft_family = False
        if 'tixcraft.com' in url:
            tixcraft_family = True

        if 'indievox.com' in url:
            tixcraft_family = True

        if 'ticketmaster.' in url:
            tixcraft_family = True

        if tixcraft_family:
            is_quit_bot = await nodriver_tixcraft_main(tab, url, config_dict, ocr, Captcha_Browser)

        if 'famiticket.com' in url:
            #fami_dict = famiticket_main(driver, url, config_dict, fami_dict)
            pass

        if 'ibon.com' in url:
            await nodriver_ibon_main(tab, url, config_dict, ocr, Captcha_Browser)

        kham_family = False
        if 'kham.com.tw' in url:
            kham_family = True

        if 'ticket.com.tw' in url:
            kham_family = True

        if 'tickets.udnfunlife.com' in url:
            kham_family = True

        if kham_family:
            #kham_main(driver, url, config_dict, ocr, Captcha_Browser)
            pass

        if 'ticketplus.com' in url:
            await nodriver_ticketplus_main(tab, url, config_dict, ocr, Captcha_Browser)

        if 'urbtix.hk' in url:
            #urbtix_main(driver, url, config_dict)
            pass

        if 'cityline.com' in url:
            tab = await nodriver_cityline_main(driver, tab, url, config_dict)

        softix_family = False
        if 'hkticketing.com' in url:
            softix_family = True
        if 'galaxymacau.com' in url:
            softix_family = True
        if 'ticketek.com' in url:
            softix_family = True
        if softix_family:
            #softix_powerweb_main(driver, url, config_dict)
            pass

        # for facebook
        facebook_login_url = 'https://www.facebook.com/login.php?'
        if url[:len(facebook_login_url)]==facebook_login_url:
            await nodriver_facebook_main(tab, config_dict)

def cli():
    parser = argparse.ArgumentParser(
            description="MaxBot Argument Parser")

    parser.add_argument("--input",
        help="config file path",
        type=str)

    parser.add_argument("--homepage",
        help="overwrite homepage setting",
        type=str)

    parser.add_argument("--ticket_number",
        help="overwrite ticket_number setting",
        type=int)

    parser.add_argument("--tixcraft_sid",
        help="overwrite tixcraft sid field",
        type=str)

    parser.add_argument("--kktix_account",
        help="overwrite kktix_account field",
        type=str)

    parser.add_argument("--kktix_password",
        help="overwrite kktix_password field",
        type=str)

    parser.add_argument("--ibonqware",
        help="overwrite ibonqware field",
        type=str)

    #default="False",
    parser.add_argument("--headless",
        help="headless mode",
        type=str)

    parser.add_argument("--browser",
        help="overwrite browser setting",
        default='',
        choices=['chrome','firefox','edge','safari','brave'],
        type=str)

    parser.add_argument("--window_size",
        help="Window size",
        type=str)

    parser.add_argument("--proxy_server",
        help="overwrite proxy server, format: ip:port",
        type=str)

    args = parser.parse_args()
    uc.loop().run_until_complete(main(args))

if __name__ == "__main__":
    cli()

