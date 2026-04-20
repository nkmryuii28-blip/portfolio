// 全タブを取得して表示
chrome.tabs.query({ currentWindow: true }, (tabs) => {
  const tabList = document.getElementById('tabList');
  const tabCount = document.getElementById('tabCount');

  tabCount.textContent = `現在のウィンドウ: ${tabs.length} タブ`;

  tabs.forEach((tab) => {
    const item = document.createElement('div');
    item.className = 'tab-item';
    item.innerHTML = `
      <div class="tab-title">${tab.title || '（タイトルなし）'}</div>
      <div class="tab-url">${tab.url}</div>
    `;
    tabList.appendChild(item);
  });

  // テキスト形式でコピー
  document.getElementById('btnCopy').addEventListener('click', () => {
    const text = tabs.map(t => `${t.title}\n${t.url}`).join('\n\n');
    navigator.clipboard.writeText(text).then(() => showToast());
  });

  // Markdown形式でコピー
  document.getElementById('btnMd').addEventListener('click', () => {
    const text = tabs.map(t => `- [${t.title}](${t.url})`).join('\n');
    navigator.clipboard.writeText(text).then(() => showToast());
  });
});

function showToast() {
  const toast = document.getElementById('toast');
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 2000);
}
