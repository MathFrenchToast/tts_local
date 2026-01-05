// popup.js for Chrome
const btnRecord = document.getElementById('btn-record');
const btnShortcuts = document.getElementById('btn-shortcuts');
const statusDiv = document.getElementById('status');

btnRecord.addEventListener('click', () => {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        if (tabs.length > 0) {
            chrome.tabs.sendMessage(tabs[0].id, {action: "toggle_recording"});
            window.close();
        } else {
            statusDiv.textContent = "Aucun onglet actif trouvé.";
        }
    });
});

btnShortcuts.addEventListener('click', () => {
    chrome.tabs.create({url: "chrome://extensions/shortcuts"});
});
