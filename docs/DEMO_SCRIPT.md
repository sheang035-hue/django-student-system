# BBU Student Management System — Presentation & Demo Script

> Full walkthrough for the final-project defense. Total time: ~10–12 minutes.
> Every step below is verified working with the `demo_data` fixture.

---

## 0. Pre-demo setup (do this 5 minutes before)

```powershell
# From the bbu-django-student-system folder, with venv activated
python manage.py loaddata demo_data        # only if the database was reset
python manage.py runserver
```

Open http://127.0.0.1:8000 in a browser, and keep a phone ready for the QR step.

### Login accounts

| Role | Username | Password |
|---|---|---|
| Administrator (staff dashboard) | `admin_staff` | your admin password |
| Instructor | `prof_sokha` / `prof_vann` | `bbu12345` |
| Demo student | `std_stu0002` … `std_stu0017` | `bbu12345` |

### Reset the database back to demo state

```powershell
python manage.py flush --noinput
python manage.py loaddata demo_data
python manage.py createsuperuser      # recreate admin_staff
```

> Tip: The QR codes encode the current host, so on `127.0.0.1` a phone cannot open them.
> For the QR scan demo either (a) deploy to Render and scan there, or (b) start the server
> with LAN access: `python manage.py runserver 0.0.0.0:8000` and add your laptop's LAN IP
> to `ALLOWED_HOSTS`, then open the site on the phone via `http://<LAN-IP>:8000`.

---

## 1. Landing page (public, no login) — 1 min

- Scroll the hero, stats band (150+/24+/12+), features and "How it works" sections.
- Point out: smooth scrolling, FAQ accordion, visible for logged-out visitors.
- Hit **Register** to show the public student registration form (don't submit).

## 2. Admin login → Dashboard — 2 min

Login as `admin_staff`. Talking points on the dashboard:

- **4 KPI cards** — totals plus the new **30-day trend chips** (▲/▼ vs previous 30 days).
- **Grade distribution** donut + **Gender ratio** chart + **Top courses** bars.
- **Recently registered students** table and Quick Actions bar.

## 3. Student directory — 1 min

- `/students/` — search "dara", show Khmer + English names, GPA pills, Active badges.
- Open a **student detail**: sidebar profile, enrollment history, and the **ID card with QR code**.
- Click **Export CSV** to show the Excel-compatible export.

## 4. Enrollment + capacity rule — 2 min

- `/enrollments/` — filter by status, search a student.
- **Create enrollment**: pick a student and course → saves and shows detail.
- **Capacity demo**: open any course, note seats taken; if a course is full, creating a new
  ENROLLED record shows the friendly bilingual error *"This course is full …"*.
  (To force it live: Admin → set a course capacity to a small number, try to enroll.)

## 5. Grade entry → transcript — 2 min

- On an enrollment, click **Add Grade** → enter score (e.g. 87) → letter grade is derived automatically.
- Open the **Official Transcript** (`Print` view): university header, MoEYS grading scale,
  cumulative GPA, academic standing, signature line, verification QR — press **Ctrl+P** to show print layout.

## 6. QR verification page (the wow moment) — 1 min

- Scan the transcript/ID-card QR with a phone (or open `/verify/STU0002/` in a new tab).
- Show the **green pulsing "Verified Student" seal**, name, ID, status, and the privacy note
  (grades/GPA are hidden on the public page).
- Also show a wrong ID (e.g. `/verify/STU9999/`) → red **"Verification Failed"** state.

## 7. Student portal — 1 min

- Log out, log in as `std_stu0002` / `bbu12345`.
- Show the personal portal: GPA ring, credit progress, grade breakdown, quick links.
- Open the dropdown → **Change Password** → change it → success page → (optional) change back.
- Toggle **dark mode** from the navbar and revisit the portal/dashboard.

## 8. Extra marks (optional) — 1 min

- **REST API**: `/api/students/`, `/api/courses/`, `/api/enrollments/` — browsable DRF interface.
- **Django admin**: `/admin/` — models registered with filters and search.
- **Tests**: run `python manage.py test students courses enrollments` → 27 passing tests.

---

## Screenshot checklist (for the written report)

Capture these at 100% zoom, light mode unless noted:

- [ ] Landing page hero (logged out)
- [ ] Dashboard with KPI trend chips visible
- [ ] Dashboard charts row (grade donut + gender + top courses)
- [ ] Students directory with search results
- [ ] Student detail page with ID card + QR
- [ ] Enrollment list with status filter chips
- [ ] Create-enrollment form (searchable selects)
- [ ] Capacity-full validation message (this proves a custom business rule)
- [ ] Add-grade form with auto letter grade
- [ ] Official transcript (print preview)
- [ ] QR verify page — verified state AND failed state
- [ ] Student portal (light) + dashboard (dark mode)
- [ ] Change-password form + success page
- [ ] DRF API browse page
- [ ] Terminal: `manage.py test` output (27 OK)

## Failure fallbacks

| Problem | Fix |
|---|---|
| Charts empty | `python manage.py loaddata demo_data` |
| QR opens login page | You scanned an old printed QR — regenerate from current app (fixture ships new URLs) |
| Phone can't open 127.0.0.1 link | Use the deployed site or LAN IP method above |
| Demo student login fails | Password is `bbu12345`; re-load the fixture if changed |
| Accidental data edits before demo | `flush` + `loaddata demo_data` + recreate superuser |
