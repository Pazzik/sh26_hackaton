from app.data.schema_card import SCHEMA_CARD

def test_schema_card_mentions_views_and_tables():
    for name in ["orders", "customers", "v_active_economic_customer",
                 "v_pnl_monthly", "v_revenue_by_line"]:
        assert name in SCHEMA_CARD
    assert len(SCHEMA_CARD) < 6000  # компактно, экономим токены
