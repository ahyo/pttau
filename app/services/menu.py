from sqlalchemy import select
from app.models.menu import MenuItem, MenuItemTR


def get_menu_tree(db, lang: str, position: str = "header", admin_logged: bool = False):
    items = (
        db.execute(
            select(MenuItem)
            .where(
                MenuItem.position.in_([position, "both"]), MenuItem.is_active == True
            )
            .order_by(
                MenuItem.parent_id.asc(),  # ✅ tanpa NULLS FIRST
                MenuItem.sort_order.asc(),
                MenuItem.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    # Filter admin-only bila belum login
    if not admin_logged:
        items = [it for it in items if not it.requires_admin]

    # ambil label sesuai lang (fallback ke en/id)
    def label_for(item):
        trs = {tr.lang: tr.label for tr in item.translations}
        return trs.get(lang) or trs.get("en") or trs.get("id") or "Menu"

    # map children
    by_parent = {}
    for it in items:
        by_parent.setdefault(it.parent_id, []).append(it)

    def build(node):
        return {
            "id": node.id,
            "label": label_for(node),
            "url": node.url,
            "is_external": node.is_external,
            "target": node.target or ("_blank" if node.is_external else "_self"),
            "icon": node.icon,
            "children": [build(ch) for ch in by_parent.get(node.id, [])],
        }

    roots = [it for it in items if it.parent_id is None]
    return [build(r) for r in roots]
