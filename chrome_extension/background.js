// background.js for Chrome
chrome.commands.onCommand.addListener((command) => {
    if (command === "toggle-recording") {
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            if (tabs.length > 0) {
                chrome.tabs.sendMessage(tabs[0].id, {action: "toggle_recording"});
            }
        });
    }
});
