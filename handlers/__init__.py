from . import admin, economy, games, joker, mines, profile, promo, rating, start


def register_handlers(dp) -> None:
    for router in (
        promo.router,
        start.router,
        games.router,
        profile.router,
        economy.router,
        rating.router,
        mines.router,
        joker.router,
        admin.router,
    ):
        dp.include_router(router)