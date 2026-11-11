// Background service worker: right-click context menu -> POST to DownieWin.
const SERVER = "http://127.0.0.1:7654/add";

async function sendToDownie(url) {
  if (!url) return;
  try {
    await fetch(SERVER, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch (e) {
    console.error("DownieWin send failed", e);
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "send-to-downie",
    title: "发送到 DownieWin",
    contexts: ["link", "video", "page"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const url = info.linkUrl || info.srcUrl || info.pageUrl || (tab && tab.url);
  sendToDownie(url);
});
