import logging
import time
from typing import Any

from playwright.sync_api import Page
from sqlalchemy.orm import Session

from app.browser.manager import browser_session_manager
from app.models.browser_page import AdBrowserPage
from app.models.browser_window import AdBrowserWindow
from app.schemas.rpa import (
    RpaLocatorCountRequest,
    RpaLocatorCountResponse,
    RpaLocatorDescribeRequest,
    RpaLocatorFindRequest,
    RpaLocatorFindResponse,
    RpaLocatorItem,
)

logger = logging.getLogger(__name__)


class RpaLocatorBackend:
    """网页 UI 元素定位后端实现。

    这里复用 BrowserSessionManager 已有的窗口运行时、页面接管、页面快照能力，
    但把“定位元素”的 DOM 扫描逻辑单独拆出来，避免继续膨胀 manager.py。
    """

    def find(self, db: Session, request: RpaLocatorFindRequest) -> RpaLocatorFindResponse:
        """按 selector、文本、标签、属性、role 等条件查找网页元素。"""
        runtime, db_window = browser_session_manager._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = browser_session_manager._resolve_rpa_page(
                db,
                db_window,
                runtime,
                request.pageId,
                request.urlContains,
            )
            if request.selector and request.selector.strip():
                items = self._collect_by_selector(page, request)
            else:
                raw_items = page.evaluate(self._scan_script(), request.model_dump())
                items = [RpaLocatorItem(**item) for item in raw_items]

            browser_session_manager._sync_page_snapshot(db, page_row, page)
            browser_session_manager._set_active_page(db, db_window, runtime, page_row.id)
            return self._response(db_window, page_row, items, request.windowId)

    def describe(self, db: Session, request: RpaLocatorDescribeRequest) -> RpaLocatorFindResponse:
        """描述 selector 命中的第一个元素。"""
        find_request = RpaLocatorFindRequest(
            windowId=request.windowId,
            pageId=request.pageId,
            urlContains=request.urlContains,
            selector=request.selector,
            visibleOnly=False,
            includeHtml=request.includeHtml,
            maxResults=1,
            timeoutMs=request.timeoutMs,
        )
        return self.find(db, find_request)

    def count(self, db: Session, request: RpaLocatorCountRequest) -> RpaLocatorCountResponse:
        """统计 selector 命中数量。"""
        runtime, db_window = browser_session_manager._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = browser_session_manager._resolve_rpa_page(
                db,
                db_window,
                runtime,
                request.pageId,
                request.urlContains,
            )
            locator = page.locator(request.selector)
            count = locator.count()
            visible_count: int | None = None
            if request.visibleOnly:
                visible_count = 0
                for index in range(count):
                    try:
                        if locator.nth(index).is_visible(timeout=request.timeoutMs):
                            visible_count += 1
                    except Exception:
                        continue
            browser_session_manager._sync_page_snapshot(db, page_row, page)
            return RpaLocatorCountResponse(
                success=True,
                selector=request.selector,
                count=visible_count if request.visibleOnly else count,
                visibleCount=visible_count,
                windowId=request.windowId,
                pageId=browser_session_manager._page_id_by_db_id(page_row.id),
            )

    def _response(
        self,
        db_window: AdBrowserWindow,
        page_row: AdBrowserPage,
        items: list[RpaLocatorItem],
        window_id: str,
    ) -> RpaLocatorFindResponse:
        return RpaLocatorFindResponse(
            success=True,
            total=len(items),
            items=items,
            windowId=window_id,
            pageId=browser_session_manager._page_id_by_db_id(page_row.id),
            title=page_row.title or '',
            url=page_row.url or '',
        )

    def _collect_by_selector(self, page: Page, request: RpaLocatorFindRequest) -> list[RpaLocatorItem]:
        """通过 Playwright locator 收集元素信息，支持 text=、xpath= 等 Playwright selector。"""
        locator = page.locator(request.selector or '')
        count = self._safe_locator_count(locator, request.timeoutMs)
        items: list[RpaLocatorItem] = []
        for index in range(min(count, request.maxResults)):
            item_locator = locator.nth(index)
            try:
                if request.visibleOnly and not item_locator.is_visible(timeout=request.timeoutMs):
                    continue
                raw_item = item_locator.evaluate(
                    self._element_info_script(),
                    {'index': len(items) + 1, 'includeHtml': request.includeHtml},
                )
                items.append(RpaLocatorItem(**raw_item))
            except Exception as exc:
                logger.debug('收集 selector 命中元素失败, selector=%s, index=%s, error=%s', request.selector, index, exc)
        return items

    @staticmethod
    def _safe_locator_count(locator: Any, timeout_ms: int) -> int:
        deadline = time.time() + timeout_ms / 1000
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                return locator.count()
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)
        if last_error:
            raise RuntimeError(f'网页元素定位失败: {last_error}') from last_error
        return 0

    @staticmethod
    def _scan_script() -> str:
        """浏览器端 DOM 扫描脚本。"""
        return r"""
        (args) => {
          const maxResults = Math.max(1, Math.min(args.maxResults || 20, 200));
          const textContains = (args.textContains || '').trim();
          const tagNames = (args.tagNames || []).map(item => String(item).toLowerCase());
          const attrName = (args.attributeName || '').trim();
          const attrValue = (args.attributeValue || '').trim();
          const attrMatch = args.attributeMatch || 'contains';
          const role = (args.role || '').trim().toLowerCase();
          const placeholder = (args.placeholder || '').trim();
          const visibleOnly = args.visibleOnly !== false;
          const includeHtml = args.includeHtml === true;

          function cssEscape(value) {
            if (window.CSS && CSS.escape) return CSS.escape(value);
            return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
          }
          function isVisible(el) {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return !!(rect.width || rect.height) && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
          }
          function semanticRole(el) {
            const explicit = (el.getAttribute('role') || '').toLowerCase();
            if (explicit) return explicit;
            const tag = el.tagName.toLowerCase();
            const type = (el.getAttribute('type') || '').toLowerCase();
            if (tag === 'button') return 'button';
            if (tag === 'a' && el.getAttribute('href')) return 'link';
            if (tag === 'input' && ['button', 'submit', 'reset'].includes(type)) return 'button';
            if (tag === 'input' || tag === 'textarea') return 'textbox';
            if (tag === 'select') return 'combobox';
            return '';
          }
          function safeAttr(value) {
            return String(value).replace(/"/g, '\\"');
          }
          function cssPath(el) {
            if (!(el instanceof Element)) return '';
            if (el.id) return '#' + cssEscape(el.id);
            const parts = [];
            let current = el;
            while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body && parts.length < 7) {
              let selector = current.nodeName.toLowerCase();
              const dataId = current.getAttribute('data-testid') || current.getAttribute('data-test') || current.getAttribute('data-cy');
              if (dataId) {
                selector += `[data-testid="${safeAttr(dataId)}"]`;
                parts.unshift(selector);
                break;
              }
              const name = current.getAttribute('name');
              if (name && ['input', 'select', 'textarea', 'button'].includes(selector)) {
                selector += `[name="${safeAttr(name)}"]`;
                parts.unshift(selector);
                break;
              }
              const classNames = Array.from(current.classList || []).slice(0, 3);
              if (classNames.length) selector += '.' + classNames.map(cssEscape).join('.');
              const parent = current.parentElement;
              if (parent) {
                const siblings = Array.from(parent.children).filter(item => item.nodeName === current.nodeName);
                if (siblings.length > 1) selector += `:nth-of-type(${siblings.indexOf(current) + 1})`;
              }
              parts.unshift(selector);
              current = parent;
            }
            return parts.join(' > ');
          }
          function attrs(el) {
            const result = {};
            ['id', 'class', 'name', 'type', 'href', 'src', 'value', 'placeholder', 'title', 'aria-label', 'role', 'data-testid', 'data-test', 'data-cy'].forEach(name => {
              const value = el.getAttribute(name);
              if (value !== null && value !== '') result[name] = value;
            });
            return result;
          }
          function suggestedSelectors(el, fallbackCss) {
            const result = [];
            const id = el.getAttribute('id');
            const dataTestId = el.getAttribute('data-testid');
            const dataTest = el.getAttribute('data-test');
            const dataCy = el.getAttribute('data-cy');
            const name = el.getAttribute('name');
            const aria = el.getAttribute('aria-label');
            const ph = el.getAttribute('placeholder');
            const tag = el.tagName.toLowerCase();
            if (id) result.push('#' + cssEscape(id));
            if (dataTestId) result.push(`[data-testid="${safeAttr(dataTestId)}"]`);
            if (dataTest) result.push(`[data-test="${safeAttr(dataTest)}"]`);
            if (dataCy) result.push(`[data-cy="${safeAttr(dataCy)}"]`);
            if (name) result.push(`${tag}[name="${safeAttr(name)}"]`);
            if (aria) result.push(`${tag}[aria-label="${safeAttr(aria)}"]`);
            if (ph) result.push(`${tag}[placeholder="${safeAttr(ph)}"]`);
            if (fallbackCss) result.push(fallbackCss);
            return Array.from(new Set(result));
          }
          function info(el, index) {
            const rect = el.getBoundingClientRect();
            const css = cssPath(el);
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 500);
            return {
              index: index,
              selector: css,
              tagName: el.tagName.toLowerCase(),
              text: text,
              visible: isVisible(el),
              enabled: !el.disabled,
              x: rect.x,
              y: rect.y,
              width: rect.width,
              height: rect.height,
              attributes: attrs(el),
              suggestedSelectors: suggestedSelectors(el, css),
              outerHtml: includeHtml ? el.outerHTML.slice(0, 3000) : null,
            };
          }

          const result = [];
          const elements = Array.from(document.querySelectorAll('body *'));
          for (const el of elements) {
            if (visibleOnly && !isVisible(el)) continue;
            const tag = el.tagName.toLowerCase();
            if (tagNames.length && !tagNames.includes(tag)) continue;
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
            if (textContains && !text.includes(textContains)) continue;
            if (attrName) {
              const current = el.getAttribute(attrName) || '';
              if (attrValue) {
                const matched = attrMatch === 'equals' ? current === attrValue : current.includes(attrValue);
                if (!matched) continue;
              } else if (!el.hasAttribute(attrName)) {
                continue;
              }
            }
            if (role && semanticRole(el) !== role) continue;
            if (placeholder && !(el.getAttribute('placeholder') || '').includes(placeholder)) continue;
            result.push(info(el, result.length + 1));
            if (result.length >= maxResults) break;
          }
          return result;
        }
        """

    @staticmethod
    def _element_info_script() -> str:
        """浏览器端单元素详情提取脚本。"""
        return r"""
        (el, args) => {
          function cssEscape(value) {
            if (window.CSS && CSS.escape) return CSS.escape(value);
            return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
          }
          function isVisible(target) {
            const rect = target.getBoundingClientRect();
            const style = window.getComputedStyle(target);
            return !!(rect.width || rect.height) && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
          }
          function safeAttr(value) {
            return String(value).replace(/"/g, '\\"');
          }
          function cssPath(target) {
            if (!(target instanceof Element)) return '';
            if (target.id) return '#' + cssEscape(target.id);
            const parts = [];
            let current = target;
            while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body && parts.length < 7) {
              let selector = current.nodeName.toLowerCase();
              const dataId = current.getAttribute('data-testid') || current.getAttribute('data-test') || current.getAttribute('data-cy');
              if (dataId) {
                selector += `[data-testid="${safeAttr(dataId)}"]`;
                parts.unshift(selector);
                break;
              }
              const name = current.getAttribute('name');
              if (name && ['input', 'select', 'textarea', 'button'].includes(selector)) {
                selector += `[name="${safeAttr(name)}"]`;
                parts.unshift(selector);
                break;
              }
              const classNames = Array.from(current.classList || []).slice(0, 3);
              if (classNames.length) selector += '.' + classNames.map(cssEscape).join('.');
              const parent = current.parentElement;
              if (parent) {
                const siblings = Array.from(parent.children).filter(item => item.nodeName === current.nodeName);
                if (siblings.length > 1) selector += `:nth-of-type(${siblings.indexOf(current) + 1})`;
              }
              parts.unshift(selector);
              current = parent;
            }
            return parts.join(' > ');
          }
          function attrs(target) {
            const result = {};
            ['id', 'class', 'name', 'type', 'href', 'src', 'value', 'placeholder', 'title', 'aria-label', 'role', 'data-testid', 'data-test', 'data-cy'].forEach(name => {
              const value = target.getAttribute(name);
              if (value !== null && value !== '') result[name] = value;
            });
            return result;
          }
          function suggestedSelectors(target, fallbackCss) {
            const result = [];
            const id = target.getAttribute('id');
            const dataTestId = target.getAttribute('data-testid');
            const dataTest = target.getAttribute('data-test');
            const dataCy = target.getAttribute('data-cy');
            const name = target.getAttribute('name');
            const aria = target.getAttribute('aria-label');
            const ph = target.getAttribute('placeholder');
            const tag = target.tagName.toLowerCase();
            if (id) result.push('#' + cssEscape(id));
            if (dataTestId) result.push(`[data-testid="${safeAttr(dataTestId)}"]`);
            if (dataTest) result.push(`[data-test="${safeAttr(dataTest)}"]`);
            if (dataCy) result.push(`[data-cy="${safeAttr(dataCy)}"]`);
            if (name) result.push(`${tag}[name="${safeAttr(name)}"]`);
            if (aria) result.push(`${tag}[aria-label="${safeAttr(aria)}"]`);
            if (ph) result.push(`${tag}[placeholder="${safeAttr(ph)}"]`);
            if (fallbackCss) result.push(fallbackCss);
            return Array.from(new Set(result));
          }
          const rect = el.getBoundingClientRect();
          const css = cssPath(el);
          return {
            index: args.index || 1,
            selector: css,
            tagName: el.tagName.toLowerCase(),
            text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 500),
            visible: isVisible(el),
            enabled: !el.disabled,
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            attributes: attrs(el),
            suggestedSelectors: suggestedSelectors(el, css),
            outerHtml: args.includeHtml ? el.outerHTML.slice(0, 3000) : null,
          };
        }
        """


rpa_locator_backend = RpaLocatorBackend()
