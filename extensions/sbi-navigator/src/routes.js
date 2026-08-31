/**
 * SBI証券で取得するファイルと、利用者への案内を定義する。
 *
 * SBI証券の認証後URLは変更されやすく、ログイン状態にも依存する。そのため、
 * この拡張機能は固定の認証後URLを推測せず、公式ポータルを開いて画面内の
 * ナビゲーションを案内する。ページのDOM、Cookie、ダウンロード内容には触れない。
 */

export const SBI_PORTAL_URL = "https://www.sbisec.co.jp/ETGate";

const ALLOWED_HOSTS = new Set(["www.sbisec.co.jp", "site2.sbisec.co.jp"]);

/**
 * 拡張機能が開いてよいSBI証券の公式URLか検証する。
 *
 * @param {string} url 検証対象のURL。
 * @returns {boolean} 許可済みのHTTPS URLの場合はtrue。
 */
export function isAllowedSbiUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && ALLOWED_HOSTS.has(parsed.hostname);
  } catch {
    return false;
  }
}

/**
 * @typedef {Object} DownloadRoute
 * @property {string} id 安定した画面識別子。
 * @property {string} title ポップアップに表示する名称。
 * @property {string} file 保存するファイルの種類。
 * @property {string[]} steps SBIポータル内での操作手順。
 */

/** @type {readonly DownloadRoute[]} */
export const DOWNLOAD_ROUTES = Object.freeze([
  {
    id: "order-history",
    title: "注文履歴",
    file: "HTML",
    steps: ["取引履歴", "注文履歴", "対象期間を表示してHTMLを保存"],
  },
  {
    id: "holdings",
    title: "保有銘柄一覧",
    file: "HTML",
    steps: ["口座管理", "保有証券一覧", "画面をHTMLで保存"],
  },
  {
    id: "executions",
    title: "約定履歴",
    file: "CSV",
    steps: ["取引履歴", "約定履歴", "CSVをダウンロード"],
  },
  {
    id: "cash-transfers",
    title: "入出金・外貨入出金",
    file: "CSV",
    steps: ["口座管理", "入出金明細", "対象のCSVをダウンロード"],
  },
  {
    id: "foreign-exchange",
    title: "為替取引注文履歴",
    file: "CSV",
    steps: ["外貨建商品", "為替取引", "注文履歴CSVをダウンロード"],
  },
]);
