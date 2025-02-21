/*
 * extension process crashes or your extension is manually stopped at
 * chrome://serviceworker-internals
 */
'use strict';

chrome.declarativeNetRequest.onRuleMatchedDebug.addListener((e) => {
    const msg = `Navigation blocked to ${e.request.url} on tab ${e.request.tabId}.`;
    //console.log(msg);
});

function reload_rule_from_setting(settings) {
    if (!settings.hasOwnProperty("domain_filter")) {
        settings.domain_filter = [];
    }
    initializeDynamicRules(settings.domain_filter);
}

chrome.runtime.onInstalled.addListener(function() {
    fetch("data/settings.json")
        .then((resp) => resp.json())
        .then((settings) => {
            reload_rule_from_setting(settings);

            chrome.storage.local.set({
                settings: settings,
            });
            console.log("dump settings.json to extension storage");
        }).catch(error => {
            console.log('error is', error)
        });
});

function initializeDynamicRules(urlsToBlock) {
    const rules = urlsToBlock.map((url, index) => ({
        "id": index + 1,
        "priority": 1,
        "action": {
            "type": "block"
        },
        "condition": {
            "urlFilter": url,
            "resourceTypes": ["main_frame", "sub_frame", "script", "image", "stylesheet", "object", "xmlhttprequest", "other"]
        }
    }));

    chrome.declarativeNetRequest.updateDynamicRules({
        removeRuleIds: rules.map(rule => rule.id),
        addRules: rules
    }, function() {
        console.log("規則已更新");
    });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    let request_json = request;
    let result_json = {
        "answer": "pong from background"
    };
    if (request_json.action == "update_role") {
        reload_rule_from_setting(request_json.data.settings);
        result_json = {
            "answer": "updating"
        };
        sendResponse(result_json);
    }
});