from sqlalchemy.orm import Session

from app.models.browser_page_config import AdBrowserPageConfig


class BrowserPageConfigMapper:

    @staticmethod
    def get_valid_configs(db: Session, config_code: str) -> list[AdBrowserPageConfig]:
        return (
            db.query(AdBrowserPageConfig)
            .filter(
                AdBrowserPageConfig.config_code == config_code,
                AdBrowserPageConfig.status == '1',
                AdBrowserPageConfig.url != '',
            )
            .order_by(AdBrowserPageConfig.sort_no.asc(), AdBrowserPageConfig.id.asc())
            .all()
        )


browser_page_config_mapper = BrowserPageConfigMapper()
