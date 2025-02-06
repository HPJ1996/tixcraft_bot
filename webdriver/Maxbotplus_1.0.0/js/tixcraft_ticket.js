const storage = chrome.storage.local;
var settings = null;

$('input[type=checkbox]').each(function() {
    $(this).prop('checked', true);
});
$("img[style='width: 100%; padding: 0;']").remove();
$("footer").remove();

function checkall() {
    $('input[type=checkbox]:not(:checked)').each(function() {
        $(this).click();
    });
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
        tixcraft_assign_ticket_number(settings);
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

    let is_ticket_number_assign = ticketmaster_ticketPriceList_ticket_number(price_keyword_array, settings.ticket_number);
    if (is_ticket_number_assign) {
        checkall();
        $("button[type='submit'].btn").click();

    }
    return is_ticket_number_assign;
}