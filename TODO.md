# Implementation Plan: Profile Section, Logout-Only Navbar & Admin Department-wise Section

## Information Gathered
- Flask app with SQLite DB, Jinja2 templating, CSS/JS in `static/`
- `/profile` route exists in `app.py` but **no Profile link in navbar** (`base.html`)
- Navbar currently shows inline trust score & streak badges (cluttered) + Logout
- `profile.html` only shows complaints stats, missing full user info (email, mobile, role, etc.)
- `complaints` table has a `department` column (added via migration) but no admin UI uses it
- Admin dashboard (`/dashboard`) has stats, charts, announcements, manage users — but no department-wise view
- `base.html` shows Login/Register for guests, but for logged-in users shows Dashboard (if admin) + trust badges + Logout

## Plan

### 1. Update `templates/base.html` (Navigation)
- Add a **Profile** link for logged-in users in the navbar
- Remove the inline trust score & streak badges from navbar (move to profile)
- Keep **Logout** as the only action button in navbar for logged-in users to keep it clean

### 2. Enhance `templates/profile.html` (User Profile)
- Display full user information card: Name, Username, Email, Mobile, Role, Member Since
- Move **Trust Score** and **Streak Days** badges from navbar to the profile header
- Keep complaint statistics (Filed, Resolved, Pending)
- Keep "My Complaints" list
- Add a **Logout** button at the bottom of the profile card

### 3. Create `templates/admin_departments.html` (Department-wise Admin View)
- Table of all complaints grouped/filterable by `department`
- Summary stats cards per department view (Total, Pending, Resolved, High Priority)
- Department filter dropdown / search
- Action buttons per complaint: View, Resolve, Delete (admin actions)
- Link from dashboard to this page

### 4. Update `templates/dashboard.html`
- Add a prominent card/button linking to the new **Department-wise Section** (`/admin/departments`)

### 5. Update `app.py` (Backend Routes & Data)
- Update `/profile` route to pass full user details (`email`, `mobile`, `role`, `created_at`) to template
- Add new route `/admin/departments` (admin-only) that:
  - Fetches distinct departments from complaints
  - Computes stats per department
  - Supports filtering by department name
  - Returns complaints for the selected department

## Dependent Files to Edit
1. `app.py`
2. `templates/base.html`
3. `templates/profile.html`
4. `templates/dashboard.html`
5. `templates/admin_departments.html` (new file)

## Follow-up Steps
- Run the app (`python app.py` or `flask run`) to verify all pages load correctly
- Check that navbar shows Profile + Logout only after login
- Check admin dashboard links to department section
- Check department filtering works

