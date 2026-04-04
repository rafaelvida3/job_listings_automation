LISTING_CARD_SELECTOR = "li[data-occludable-job-id]"
LISTING_LINK_SELECTOR = "a.job-card-list__title--link"
DETAIL_TITLE_SELECTOR = (
    "div.job-details-jobs-unified-top-card__job-title h1 a, "
    "div.job-details-jobs-unified-top-card__job-title h1"
)
DETAIL_DESCRIPTION_SELECTOR = "#job-details"
PAGINATION_STATE_SELECTOR = ".jobs-search-pagination__page-state"
NEXT_PAGE_BUTTON_SELECTOR = (
    "button.jobs-search-pagination__button--next, "
    "button[aria-label='Ver próxima página'], "
    "button[aria-label='View next page']"
)
EMPTY_RESULTS_TEXTS = (
    "Nenhuma vaga corresponde aos seus critérios",
    "No jobs match your criteria",
    "Aucun poste ne correspond à vos critères",
)