const SERVER = "http://127.0.0.1:7654/add";

async function sendCurrent() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab && (tab.url || tab.pendingUrl);
  const status = document.getElementById("status");
  if (!url) {
    status.textContent = "无法获取当前页面地址。";
    return;
  }
  try {
    await fetch(SERVER, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    status.textContent = "已发送：" + url.slice(0, 50);
  } catch (e) {
    status.textContent = "发送失败，请确认 DownieWin 正在运行。";
  }
}

document.getElementById("send").addEventListener("click", sendCurrent);
