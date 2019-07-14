// Copyright 2018 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

'use strict';
var url;
var socket = new WebSocket("ws://127.0.0.1:5678");
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
	if(changeInfo.url !== undefined) {
 		socket.send('onUpdated,' + changeInfo.url);
	}
}); 

chrome.tabs.onActivated.addListener(function(activeInfo) {
  chrome.tabs.get(activeInfo.tabId, function(tab){
  	if(tab.url !== undefined) {
    	socket.send('onActivated,' + tab.url);
  	}
  });
});
socket.onmessage = function(event) {
	console.log(event.data);
	if(event.data === 'getTab') {
		chrome.tabs.getCurrent(function(tab) {
            if(tab.url !== undefined) {
                socket.send(tab.url)
            }
        });
	}
};
