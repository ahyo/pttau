from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.menu import MenuItem
from app.ui import localized_attr


def _is_path_active(url: str | None, current_path: str | None) -> bool:
    if not url or not current_path:
        return False
    normalized_item = url if url == "/" else url.rstrip("/")
    normalized_current = current_path if current_path == "/" else current_path.rstrip("/")
    return normalized_current == normalized_item or (
        normalized_item != "/" and normalized_current.startswith(normalized_item + "/")
    )


def get_menu_tree(
    db,
    lang: str,
    position: str = "header",
    admin_logged: bool = False,
    current_path: str | None = None,
):
    items = (
        db.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.translations))
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

    # map children
    by_parent = {}
    for it in items:
        by_parent.setdefault(it.parent_id, []).append(it)

    def build(node):
        children = [build(ch) for ch in by_parent.get(node.id, [])]
        active = _is_path_active(node.url, current_path) or any(
            ch["active"] for ch in children
        )
        return {
            "id": node.id,
            "label": localized_attr(node, lang, "label") or "Menu",
            "url": node.url,
            "is_external": node.is_external,
            "target": node.target or ("_blank" if node.is_external else "_self"),
            "icon": node.icon,
            "children": children,
            "active": active,
        }

    roots = [it for it in items if it.parent_id is None]
    return [build(r) for r in roots]
