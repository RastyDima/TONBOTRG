from . import admin, economy, games, joker, mines, profile, rating, start


def register_handlers(dp) -> None:
    for router in (
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