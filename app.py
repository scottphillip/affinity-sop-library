"""
Affinity Group - SOP & Knowledge Base
======================================
Internal documentation hub organized by division, region, and topic.
Content is stored in Snowflake and rendered inline as markdown.
"""
import streamlit as st
import json
import hashlib
import snowflake.connector
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="SOP & Knowledge Base | Affinity Group",
    page_icon="📚",
    layout="wide",
)

# Brand colors
ORANGE = "#F5921E"
CHARCOAL = "#2D2D2D"

USERS_TABLE = "DB_PROD_TRF.SCH_TRF_UTILS.TB_TICKET_APP_USERS"
KB_TABLE = "DB_PROD_TRF.SCH_TRF_UTILS.TB_SOP_KNOWLEDGE_BASE"
LINKS_TABLE = "DB_PROD_TRF.SCH_TRF_UTILS.TB_SOP_LINKS"
ADMIN_EMAIL = "scott.phillips@affinitysales.com"

# Predefined sections and categories
SECTIONS = {
    "CSS": ["Order Entry", "Import Servers", "General Processes", "Troubleshooting"],
    "Regions": ["Northeast", "Southeast", "Central", "West"],
    "Consolidated Client Scorecard": ["General Process", "Special Conditions by Client", "Notable Downstream Effects"],
    "CRM": ["General", "Data Management", "Integrations"],
    "Order Management": ["Imports"],
    "Sales Enablement Tools": ["DAX & Power BI Fundamentals", "Fiscal Years", "Navigation & How Things Work", "Report Building"],
    "Links & Resources": [],
}

# Import template files available for download
IMPORT_TEMPLATES_DIR = Path(__file__).parent / "import_templates"


# ─── Snowflake Connection ───
@st.cache_resource
def get_snowflake_conn():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        role=st.secrets["snowflake"]["role"],
    )


def run_query(sql: str, params: tuple = None):
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception:
        st.cache_resource.clear()
        conn = get_snowflake_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def run_dml(sql: str, params: tuple = None):
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
    except Exception:
        st.cache_resource.clear()
        conn = get_snowflake_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
    finally:
        cur.close()


# ─── Employee Directory ───
@st.cache_data
def load_employee_directory():
    dir_path = Path(__file__).parent / "employee_directory.json"
    if dir_path.exists():
        with open(dir_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─── Auth Functions ───
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def check_user_exists(email: str) -> bool:
    rows = run_query(f"SELECT 1 FROM {USERS_TABLE} WHERE EMAIL = %s", (email,))
    return len(rows) > 0


def verify_password(email: str, password: str) -> bool:
    rows = run_query(f"SELECT PASSWORD_HASH FROM {USERS_TABLE} WHERE EMAIL = %s", (email,))
    if not rows:
        return False
    return rows[0][0] == hash_password(password)


def create_user(email: str, display_name: str, password: str):
    run_dml(
        f"INSERT INTO {USERS_TABLE} (EMAIL, DISPLAY_NAME, PASSWORD_HASH) VALUES (%s, %s, %s)",
        (email, display_name, hash_password(password))
    )


# ─── Knowledge Base Functions ───
@st.cache_data(ttl=60)
def get_all_articles():
    """Get all KB articles."""
    return run_query(
        f"SELECT ID, SECTION, CATEGORY, TITLE, CONTENT, AUTHOR, CREATED_AT, UPDATED_AT, SORT_ORDER "
        f"FROM {KB_TABLE} ORDER BY SECTION, CATEGORY, SORT_ORDER, TITLE"
    )


def get_article_by_id(article_id: int):
    rows = run_query(f"SELECT ID, SECTION, CATEGORY, TITLE, CONTENT, AUTHOR, CREATED_AT FROM {KB_TABLE} WHERE ID = %s", (article_id,))
    return rows[0] if rows else None


def save_article(section: str, category: str, title: str, content: str, author: str):
    run_dml(
        f"INSERT INTO {KB_TABLE} (SECTION, CATEGORY, TITLE, CONTENT, AUTHOR) VALUES (%s, %s, %s, %s, %s)",
        (section, category, title, content, author)
    )
    st.cache_data.clear()


def update_article(article_id: int, section: str, category: str, title: str, content: str):
    run_dml(
        f"UPDATE {KB_TABLE} SET SECTION=%s, CATEGORY=%s, TITLE=%s, CONTENT=%s, UPDATED_AT=CURRENT_TIMESTAMP() WHERE ID=%s",
        (section, category, title, content, article_id)
    )
    st.cache_data.clear()


def delete_article(article_id: int):
    run_dml(f"DELETE FROM {KB_TABLE} WHERE ID = %s", (article_id,))
    st.cache_data.clear()


@st.cache_data(ttl=60)
def get_all_links():
    return run_query(f"SELECT ID, SECTION, TITLE, URL, DESCRIPTION, CREATED_AT FROM {LINKS_TABLE} ORDER BY SECTION, TITLE")


def save_link(section: str, title: str, url: str, description: str):
    run_dml(
        f"INSERT INTO {LINKS_TABLE} (SECTION, TITLE, URL, DESCRIPTION) VALUES (%s, %s, %s, %s)",
        (section, title, url, description)
    )
    st.cache_data.clear()


def delete_link(link_id: int):
    run_dml(f"DELETE FROM {LINKS_TABLE} WHERE ID = %s", (link_id,))
    st.cache_data.clear()


def search_articles(query: str):
    """Search articles by title or content."""
    q = f"%{query}%"
    return run_query(
        f"SELECT ID, SECTION, CATEGORY, TITLE, CONTENT FROM {KB_TABLE} "
        f"WHERE TITLE ILIKE %s OR CONTENT ILIKE %s ORDER BY SECTION, TITLE",
        (q, q)
    )


# ─── LOGIN PAGE ───
def show_login():
    st.markdown(f"""
    <div style="background: {CHARCOAL}; padding: 15px 25px; border-radius: 10px; margin-bottom: 25px;">
        <span style="color: {ORANGE}; font-size: 22px; font-weight: bold;">AFFINITY GROUP</span>
        <span style="color: white; font-size: 22px; font-weight: 300;"> KNOWLEDGE BASE</span>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="yourname@affinitysales.com", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            login_btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if login_btn:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                email_lower = email.strip().lower()
                directory = load_employee_directory()
                if email_lower not in directory:
                    st.error("Email not found in the Affinity Group directory.")
                elif not check_user_exists(email_lower):
                    st.warning("No account found. Please create an account first.")
                elif not verify_password(email_lower, password):
                    st.error("Incorrect password.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email_lower
                    st.session_state.user_name = directory[email_lower]
                    st.rerun()

    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input("Email", placeholder="yourname@affinitysales.com", key="reg_email")
            reg_pw = st.text_input("Create Password", type="password", key="reg_pw")
            reg_pw2 = st.text_input("Confirm Password", type="password", key="reg_pw2")
            register_btn = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if register_btn:
            if not reg_email or not reg_pw:
                st.error("Please fill in all fields.")
            elif reg_pw != reg_pw2:
                st.error("Passwords do not match.")
            elif len(reg_pw) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                email_lower = reg_email.strip().lower()
                directory = load_employee_directory()
                if email_lower not in directory:
                    st.error("Email not found in the Affinity Group directory.")
                elif check_user_exists(email_lower):
                    st.warning("Account already exists. Please sign in.")
                else:
                    create_user(email_lower, directory[email_lower], reg_pw)
                    st.session_state.logged_in = True
                    st.session_state.user_email = email_lower
                    st.session_state.user_name = directory[email_lower]
                    st.rerun()


# ─── MAIN APP ───
def show_main_app():
    user_name = st.session_state.user_name
    user_email = st.session_state.user_email
    is_admin = (user_email == ADMIN_EMAIL)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"""
        <div style="background: {CHARCOAL}; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px;">
            <span style="color: {ORANGE}; font-size: 16px; font-weight: bold;">AFFINITY</span>
            <span style="color: white; font-size: 16px;"> KNOWLEDGE BASE</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**{user_name}**")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")

        # Search
        search_query = st.text_input("🔍 Search", placeholder="Search articles...")

        st.markdown("---")

        # Navigation
        nav_options = list(SECTIONS.keys())
        if is_admin:
            nav_options.append("✏️ Admin")

        selected_section = st.radio("Sections", nav_options, label_visibility="collapsed")

    # ── Main Content ──
    if search_query:
        show_search_results(search_query)
    elif selected_section == "✏️ Admin":
        show_admin_panel()
    elif selected_section == "Links & Resources":
        show_links_section(is_admin)
    else:
        show_section_content(selected_section, is_admin)


def show_search_results(query: str):
    """Show search results."""
    st.markdown(f"### Search Results for: *{query}*")
    results = search_articles(query)
    if not results:
        st.info("No articles found matching your search.")
    else:
        st.markdown(f"Found **{len(results)}** result(s)")
        for r in results:
            article_id, section, category, title, content = r
            with st.expander(f"**{title}** — {section} > {category}"):
                st.markdown(content[:500] + ("..." if len(content) > 500 else ""))
                if st.button("Read Full Article", key=f"read_{article_id}"):
                    st.session_state.viewing_article = article_id
                    st.rerun()


def show_import_templates():
    """Show downloadable import template files."""
    if not IMPORT_TEMPLATES_DIR.exists():
        return
    templates = sorted(IMPORT_TEMPLATES_DIR.glob("*.*"))
    if not templates:
        return
    st.markdown("### Import Templates")
    st.caption("Download blank templates for TELUS OMS import utilities.")
    cols = st.columns(min(len(templates), 3))
    for i, tpl in enumerate(templates):
        with cols[i % 3]:
            with open(tpl, "rb") as f:
                st.download_button(
                    label=f"📥 {tpl.stem}",
                    data=f.read(),
                    file_name=tpl.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{tpl.name}",
                    use_container_width=True,
                )
    st.markdown("---")


def show_section_content(section: str, is_admin: bool):
    """Show articles for a section, organized by category."""
    st.markdown(f"## {section}")

    # Show import template downloads for Order Management
    if section == "Order Management":
        show_import_templates()

    articles = get_all_articles()
    section_articles = [a for a in articles if a[1] == section]

    if not section_articles:
        st.info(f"No documentation yet for **{section}**. "
                + ("Use the Admin panel to add content." if is_admin else "Check back later!"))
        return

    # Group by category
    categories = {}
    for a in section_articles:
        cat = a[2] or "General"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)

    # Show categories
    for cat_name in sorted(categories.keys()):
        st.markdown(f"### {cat_name}")
        for article in categories[cat_name]:
            article_id, _, _, title, content, author, created, updated, sort_order = article
            with st.expander(f"📄 {title}"):
                st.markdown(content)
                st.markdown("---")
                meta_parts = []
                if author:
                    meta_parts.append(f"Author: {author}")
                if updated:
                    meta_parts.append(f"Updated: {updated.strftime('%b %d, %Y')}")
                elif created:
                    meta_parts.append(f"Created: {created.strftime('%b %d, %Y')}")
                if meta_parts:
                    st.caption(" | ".join(meta_parts))

                if is_admin:
                    col_edit, col_del = st.columns([1, 1])
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_{article_id}"):
                            st.session_state.editing_article = article_id
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_{article_id}"):
                            delete_article(article_id)
                            st.success("Article deleted.")
                            st.rerun()


def show_links_section(is_admin: bool):
    """Show the Links & Resources section."""
    st.markdown("## Links & Resources")
    st.markdown("Important links and bookmarks organized by topic.")

    links = get_all_links()

    if not links:
        st.info("No links saved yet." + (" Use Admin to add links." if is_admin else ""))
    else:
        # Group by section
        grouped = {}
        for l in links:
            link_id, section, title, url, desc, created = l
            if section not in grouped:
                grouped[section] = []
            grouped[section].append(l)

        for section_name in sorted(grouped.keys()):
            st.markdown(f"### {section_name}")
            for l in grouped[section_name]:
                link_id, _, title, url, desc, created = l
                col_link, col_action = st.columns([6, 1])
                with col_link:
                    st.markdown(f"🔗 [{title}]({url})")
                    if desc:
                        st.caption(desc)
                with col_action:
                    if is_admin:
                        if st.button("🗑️", key=f"dellink_{link_id}"):
                            delete_link(link_id)
                            st.rerun()

    # Admin: add new link
    if is_admin:
        st.markdown("---")
        st.markdown("#### Add New Link")
        with st.form("add_link_form", clear_on_submit=True):
            link_section = st.text_input("Section/Category", placeholder="e.g., Power BI, SharePoint, Tools")
            link_title = st.text_input("Link Title", placeholder="e.g., Power BI Service")
            link_url = st.text_input("URL", placeholder="https://...")
            link_desc = st.text_input("Description (optional)", placeholder="Brief description")
            if st.form_submit_button("Add Link", type="primary"):
                if link_section and link_title and link_url:
                    save_link(link_section, link_title, link_url, link_desc)
                    st.success("Link added!")
                    st.rerun()
                else:
                    st.error("Section, title, and URL are required.")


def show_admin_panel():
    """Admin panel for managing content."""
    st.markdown("## Admin Panel")

    # Check if editing an article
    if "editing_article" in st.session_state and st.session_state.editing_article:
        show_edit_article(st.session_state.editing_article)
        return

    tab_new, tab_manage = st.tabs(["New Article", "Manage Articles"])

    with tab_new:
        st.markdown("### Create New Article")
        with st.form("new_article_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                section = st.selectbox("Section", [s for s in SECTIONS.keys() if s != "Links & Resources"])
            with col2:
                # Dynamic categories based on section
                categories = SECTIONS.get(section, [])
                if categories:
                    category = st.selectbox("Category", categories + ["Other"])
                else:
                    category = st.text_input("Category", placeholder="e.g., General")

            title = st.text_input("Title", placeholder="Article title")
            content = st.text_area(
                "Content (Markdown supported)",
                height=400,
                placeholder="Write your article here...\n\n"
                            "You can use **bold**, *italic*, `code`, lists, headers, and more.\n\n"
                            "## Sub-heading\n"
                            "- Bullet point\n"
                            "1. Numbered list\n\n"
                            "```\nCode block\n```",
            )

            if st.form_submit_button("Publish Article", type="primary", use_container_width=True):
                if not title or not content:
                    st.error("Title and content are required.")
                else:
                    if category == "Other":
                        category = "General"
                    save_article(section, category, title, content, st.session_state.user_name)
                    st.success(f"Article '{title}' published!")
                    st.rerun()

    with tab_manage:
        st.markdown("### All Articles")
        articles = get_all_articles()
        if not articles:
            st.info("No articles yet. Create one above!")
        else:
            for a in articles:
                article_id, section, category, title, content, author, created, updated, sort_order = a
                col_info, col_actions = st.columns([5, 2])
                with col_info:
                    st.markdown(f"**{title}** — {section} > {category}")
                    st.caption(f"By {author or 'Unknown'} | {created.strftime('%b %d, %Y') if created else ''}")
                with col_actions:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️", key=f"adm_edit_{article_id}"):
                            st.session_state.editing_article = article_id
                            st.rerun()
                    with c2:
                        if st.button("🗑️", key=f"adm_del_{article_id}"):
                            delete_article(article_id)
                            st.rerun()
                st.markdown("---")


def show_edit_article(article_id: int):
    """Edit an existing article."""
    article = get_article_by_id(article_id)
    if not article:
        st.error("Article not found.")
        st.session_state.editing_article = None
        return

    _, section, category, title, content, author, created = article

    st.markdown(f"### Editing: {title}")

    if st.button("← Back to Admin"):
        st.session_state.editing_article = None
        st.rerun()

    with st.form("edit_article_form"):
        col1, col2 = st.columns(2)
        with col1:
            sections_list = [s for s in SECTIONS.keys() if s != "Links & Resources"]
            section_idx = sections_list.index(section) if section in sections_list else 0
            new_section = st.selectbox("Section", sections_list, index=section_idx)
        with col2:
            new_category = st.text_input("Category", value=category or "")

        new_title = st.text_input("Title", value=title)
        new_content = st.text_area("Content (Markdown)", value=content, height=400)

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                update_article(article_id, new_section, new_category, new_title, new_content)
                st.session_state.editing_article = None
                st.success("Article updated!")
                st.rerun()
        with col_cancel:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state.editing_article = None
                st.rerun()


# ─── MAIN ───
if st.session_state.get("logged_in"):
    show_main_app()
else:
    show_login()
