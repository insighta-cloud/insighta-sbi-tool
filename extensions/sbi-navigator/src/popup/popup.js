import { DOWNLOAD_ROUTES, SBI_PORTAL_URL, isAllowedSbiUrl } from "../routes.js";

const routeList = document.querySelector("#route-list");
const status = document.querySelector("#status");

/**
 * 許可済みの公式URLだけを新しいタブで開く。
 * URLの生成元をroutes.jsに限定し、任意URLを開く経路を作らない。
 *
 * @param {string} url 開くURL。
 * @param {string} message 利用者に表示する結果メッセージ。
 */
async function openOfficialPage(url, message) {
  if (!isAllowedSbiUrl(url)) {
    status.textContent = "安全確認に失敗したため、ページを開きませんでした。";
    return;
  }

  await chrome.tabs.create({ url });
  status.textContent = message;
}

function renderRoutes() {
  for (const route of DOWNLOAD_ROUTES) {
    const article = document.createElement("article");
    article.className = "route";

    const heading = document.createElement("h3");
    heading.textContent = `${route.title} (${route.file})`;

    const steps = document.createElement("ol");
    for (const step of route.steps) {
      const item = document.createElement("li");
      item.textContent = step;
      steps.append(item);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = "SBIポータルを開く";
    button.addEventListener("click", () => {
      void openOfficialPage(SBI_PORTAL_URL, `${route.title}の案内を表示しています。`);
    });

    article.append(heading, steps, button);
    routeList.append(article);
  }
}

document.querySelector("#open-portal").addEventListener("click", () => {
  void openOfficialPage(SBI_PORTAL_URL, "SBI証券の公式ログイン画面を開きました。");
});

renderRoutes();
