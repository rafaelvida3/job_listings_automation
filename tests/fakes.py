from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class FakeLocator:
    def __init__(
        self,
        items: list[Any] | None = None,
        text: str = "",
        visible: bool = True,
    ) -> None:
        self.items = items or []
        self.text = text
        self.visible = visible
        self.clicked = False
        self.scrolled = False
        self.evaluated_scripts: list[tuple[str, Any]] = []
        self.href: str | None = None

    @property
    def first(self) -> Any:
        return self.items[0] if self.items else self

    def count(self) -> int:
        if self.items:
            return len(self.items)
        return 1 if self.text or self.href is not None else 0

    def nth(self, index: int) -> Any:
        return self.items[index]

    def inner_text(self, timeout: int = 0) -> str:
        return self.text

    def is_visible(self) -> bool:
        return self.visible

    def click(self, timeout: int = 0) -> None:
        self.clicked = True

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        self.scrolled = True

    def evaluate(self, script: str, value: Any = None) -> None:
        self.evaluated_scripts.append((script, value))

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        return None

    def locator(self, selector: str) -> FakeLocator:
        return self


class BrokenLocator(FakeLocator):
    def inner_text(self, timeout: int = 0) -> str:
        raise RuntimeError("locator is stale")


class FakeLinkLocator(FakeLocator):
    def __init__(self, text: str = "", href: str | None = None) -> None:
        super().__init__(text=text)
        self.href = href


class FakeCard:
    def __init__(
        self,
        listing_id: str = "",
        fallback_title: str = "",
        fallback_href: str | None = None,
    ) -> None:
        self.attributes = {
            "data-occludable-job-id": listing_id,
            "data-job-id": "",
        }
        self.link_locator = FakeLinkLocator(text=fallback_title, href=fallback_href)
        self.clicked = False
        self.scrolled = False
        self.evaluated_scripts: list[tuple[str, Any]] = []

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def locator(self, selector: str) -> FakeLocator:
        return self.link_locator

    def click(self, timeout: int = 0) -> None:
        self.clicked = True

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        self.scrolled = True

    def evaluate(self, script: str, value: Any = None) -> None:
        self.evaluated_scripts.append((script, value))


class BrokenScrollCard(FakeCard):
    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        raise RuntimeError("scroll failed")


class FakeMouse:
    def wheel(self, delta_x: float, delta_y: float) -> None:
        return None
    

class FakePage:
    def __init__(
        self,
        *,
        locator_map: dict[str, Any] | None = None,
        text_map: dict[str, FakeLocator] | None = None,
    ) -> None:
        self.locator_map = locator_map or {}
        self.text_map = text_map or {}
        self.mouse = MagicMock()
        self.waited_timeouts: list[int] = []
        self.waited_selectors: list[tuple[str, int | None]] = []
        self.waited_functions: list[dict[str, Any]] = []
        self.goto_calls: list[tuple[str, str | None]] = []
        self.screenshot_calls: list[dict[str, Any]] = []

    def locator(self, selector: str) -> Any:
        return self.locator_map[selector]

    def get_by_text(self, text: str, exact: bool = False) -> FakeLocator:
        return self.text_map.get(text, FakeLocator())

    def wait_for_timeout(self, timeout: int) -> None:
        self.waited_timeouts.append(timeout)

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> None:
        self.waited_selectors.append((selector, timeout))

    def wait_for_function(self, script: str, arg: dict[str, Any], timeout: int) -> None:
        self.waited_functions.append({"script": script, "arg": arg, "timeout": timeout})

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.goto_calls.append((url, wait_until))

    def screenshot(self, path: str, full_page: bool) -> None:
        self.screenshot_calls.append({"path": path, "full_page": full_page})


class BrokenContext:
    def close(self) -> None:
        raise RuntimeError("close failed")
