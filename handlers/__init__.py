from . import admin, alchemist, economy, games, joker, mines, profile, promo, rating, ruby_roulette, start


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
        alchemist.router,
        ruby_roulette.router,
        admin.router,
    ):
        dp.include_router(router)