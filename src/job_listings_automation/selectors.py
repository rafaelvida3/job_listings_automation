from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SelectorProfile:
    listing_card: str
    listing_link: str
    detail_title: str
    detail_description: str
    pagination_state: str
    next_page_button: str
    empty_results_texts: tuple[str, ...]


DEFAULT_SELECTOR_PROFILE = SelectorProfile(
    listing_card="li[data-occludable-job-id]",
    listing_link="a.job-card-list__title--link",
    detail_title=(
        "div.job-details-jobs-unified-top-card__job-title h1 a, "
        "div.job-details-jobs-unified-top-card__job-title h1"
    ),
    detail_description="#job-details",
    pagination_state=".jobs-search-pagination__page-state",
    next_page_button=(
        "button.jobs-search-pagination__button--next, "
        "button[aria-label='Ver próxima página'], "
        "button[aria-label='View next page']"
    ),
    empty_results_texts=(
        "Nenhuma vaga corresponde aos seus critérios",
        "No jobs match your criteria",
        "Aucun poste ne correspond à vos critères",
    ),
)
