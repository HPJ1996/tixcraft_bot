const storage = chrome.storage.local;
var settings = null;

$('input[type=checkbox]').each(function() {
    $(this).prop('checked', true);
});
$("img[style='width: 100%; padding: 0;']").remove();
$("footer").remove();

var ticketmaster_ocr_interval = null;
var ticketmaster_ocr_config = {
    captcha_length: 4,
    captcha_selector: "#TicketForm_verifyCode-image",
    captcha_renew_selector: "#TicketForm_verifyCode-image",
    input_selector: "#TicketForm_verifyCode",
    submit_selector: "button[type='submit']"
};

function get_ticketmaster_ocr_image() {
    // due to multi format
    let captcha_selector = ticketmaster_ocr_config.captcha_selector;

    let image_data = "";
    //console.log(captcha_selector);
    let img = document.querySelector(captcha_selector);
    if (img != null) {
        let canvas = document.createElement('canvas');
        let context = canvas.getContext('2d');
        canvas.height = img.naturalHeight;
        canvas.width = img.naturalWidth;
        context.drawImage(img, 0, 0);
        let img_data = canvas.toDataURL();
        if (img_data) {
            image_data = img_data.split(",")[1];
            //console.log(image_data);
        }
    } else {
        // console.log("img not found:" + tzuchi_ocr_config.captcha_selector);
    }
    return image_data;
}

var last_ticketmaster_captcha_answer = "";
chrome.runtime.onMessage.addListener((message) => {
    let captcha_renew_selector = ticketmaster_ocr_config.captcha_renew_selector;

    //console.log('sent from background', message);
    if (message && message.hasOwnProperty("answer")) {
        let is_valid_anwser = false;
        if (message.answer.length == ticketmaster_ocr_config.captcha_length) {
            is_valid_anwser = true;
        }
        //console.log(is_valid_anwser);
        if (is_valid_anwser) {
            ticketmaster_set_ocr_answer(message.answer);
            last_ticketmaster_captcha_answer = message.answer;
        } else {
            // renew captcha.
            if (last_ticketmaster_captcha_answer != message.answer) {
                last_ticketmaster_captcha_answer = message.answer;
                console.log("renew captcha: " + captcha_renew_selector);
                if ($(captcha_renew_selector).length) {
                    $(captcha_renew_selector).click();
                }
                ticketmaster_ticket_main();
            }
        }
    }
});

function checkall() {
    $('input[type=checkbox]:not(:checked)').each(function() {
        $(this).click();
    });
}

function ticketmaster_set_ocr_answer(answer) {
    let input_selector = ticketmaster_ocr_config.input_selector;
    let submit_selector = ticketmaster_ocr_config.submit_selector;
    //console.log("answer:"+answer);
    if (answer.length > 0) {
        let sendkey_by_webdriver = false;
        if (settings) {
            if (settings.hasOwnProperty("token")) {
                sendkey_by_webdriver = true;
            }
        }
        //console.log("sendkey_by_webdriver:"+sendkey_by_webdriver);
        if (!sendkey_by_webdriver) {
            // solution #1: javascript.
            $(input_selector).val(answer);
            $(submit_selector).click();
        } else {
            // solution #2: click webdriver.
            webdriver_location_sendkey(settings, input_selector, answer, document.location.href);
            //webdriver_location_click(settings, submit_selector, document.location.href);
            $(input_selector).val(answer);
            $(submit_selector).click();
        }
    }
}

async function ticketmaster_get_ocr_answer(api_url, image_data) {
    let bundle = {
        action: 'ocr',
        data: {
            'url': api_url + 'ocr',
            'image_data': image_data,
        }
    };
    const return_answer = await chrome.runtime.sendMessage(bundle);
}

function ticketmaster_ticketPriceList_clean_exclude(exclude_keyword_array) {
    for (let i = 0; i < exclude_keyword_array.length; i++) {
        $("#ticketPriceList > tbody > tr").each(function() {
            let html_text = $(this).text();
            //console.log("html:"+html_text);
            if (html_text.indexOf(exclude_keyword_array[i]) > -1) {
                $(this).remove();
            }
        });
    }
}

function ticketmaster_ticketPriceList_ticket_number(price_keyword_array, ticket_number) {
    let is_ticket_number_assign = false;

    let target_row = null;
    let all_row = $("#ticketPriceList > tbody > tr");
    if (all_row.length > 0) {
        if (all_row.length == 1) {
            // single select.
            target_row = all_row;
        } else {
            // multi select.
            all_row.each(function() {
                let is_match_keyword = false;
                if (price_keyword_array.length) {
                    let html_text = $(this).text();
                    for (let i = 0; i < price_keyword_array.length; i++) {
                        if (price_keyword_array[i].indexOf(" ") > -1) {
                            // TODO: muti keywords with AND logic.
                        } else {
                            if (html_text.indexOf(price_keyword_array[i]) > -1) {
                                is_match_keyword = true;
                                target_row = $(this);
                                break;
                            }
                        }
                    }
                } else {
                    if (all_row.index(this) == 0) {
                        is_match_keyword = true;
                        target_row = $(this);
                    }
                }
                //console.log("is_match_keyword:"+is_match_keyword);
                if (is_match_keyword) {
                    return;
                }
            });
        }

        let ticket_options = target_row.find("option");
        if (ticket_options.length) {
            const first_option = ticket_options.first();

            if (ticket_number > 0 && first_option.prop('selected') && first_option.prop('value') == '0') {
                ticket_options.each(function() {
                    if ($(this).val() == ticket_number) {
                        $(this).prop('selected', true);
                        is_ticket_number_assign = true;
                        return false;
                    }
                });
            }
            if (!is_ticket_number_assign) {
                ticket_options.last().prop('selected', true);
            }
        }
    }
    return is_ticket_number_assign;
}

function ticketmaster_orc_image_ready(api_url) {
    let ret = false;
    let image_data = get_ticketmaster_ocr_image();
    if (image_data.length > 0) {
        ret = true;
        if (ticketmaster_ocr_interval) clearInterval(ticketmaster_ocr_interval);
        ticketmaster_get_ocr_answer(api_url, image_data);
    }
    //console.log("orc_image_ready:"+ret);
    return ret;
}

function ticketmaster_ticket_main() {
    let remote_url_string = get_remote_url(settings);
    ticketmaster_ocr_interval = setInterval(() => {
        storage.get('status', function(items) {
            if (items.status && items.status == 'ON') {
                ticketmaster_orc_image_ready(remote_url_string);
            } else {
                console.log('ddddext status is not OFF');
            }
        });
    }, 100);
}

storage.get('settings', function(items) {
    if (items.settings) {
        settings = items.settings;

        tixcraft_ticket_clean_exclude(settings);
        let is_ticket_number_assign = tixcraft_assign_ticket_number(settings);
        if (is_ticket_number_assign) {
            checkall();
            if ($("#TicketForm_verifyCode").length) {
                ticketmaster_ticket_main();
            } else {
                $("button[type='submit'].btn").click();
            }
        }
    }
});

function tixcraft_ticket_clean_exclude(settings) {
    let exclude_keyword_array = [];
    if (settings) {
        if (settings.keyword_exclude.length > 0) {
            if (settings.keyword_exclude != '""') {
                exclude_keyword_array = JSON.parse('[' + settings.keyword_exclude + ']');
            }
        }
    }
    ticketmaster_ticketPriceList_clean_exclude(exclude_keyword_array);
}

function tixcraft_assign_ticket_number(settings) {
    let price_keyword_array = [];
    if (settings) {
        if (settings.area_auto_select.area_keyword.length > 0) {
            if (settings.area_auto_select.area_keyword != '""') {
                price_keyword_array = JSON.parse('[' + settings.area_auto_select.area_keyword + ']');
            }
        }
    }

    return ticketmaster_ticketPriceList_ticket_number(price_keyword_array, settings.ticket_number);
}
