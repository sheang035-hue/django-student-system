from datetime import date

GRADE_POINTS = {
    'A': 4.00,
    'B+': 3.50,
    'B': 3.00,
    'C+': 2.50,
    'C': 2.00,
    'D': 1.50,
    'F': 0.00,
}

COURSE_KHMER_MAP = {
    'CS101': 'សេចក្តីផ្តើមវិទ្យាសាស្ត្រកុំព្យូទ័រ',
    'WD201': 'មូលដ្ឋានគ្រឹះនៃការអភិវឌ្ឍវេបសាយ',
    'DB202': 'ប្រព័ន្ធគ្រប់គ្រងមូលដ្ឋានទិន្នន័យ',
    'PY204': 'ការសរសេរកម្មវិធី Python',
    'NET203': 'ប្រព័ន្ធបណ្តាញកុំព្យូទ័រ',
}

STANDING_BANDS = [
    (3.80, 'Highest Distinction (Summa Cum Laude)', 'ល្អប្រសើរដាច់គេ', 'success', 'Excellent'),
    (3.50, 'High Distinction (Magna Cum Laude)', 'ល្អប្រសើរ', 'success', 'Very Good'),
    (3.00, 'Distinction (Cum Laude)', 'ល្អណាស់', 'primary', 'Good'),
    (2.50, 'Good Standing', 'ល្អបង្គួរ', 'info', 'Fair'),
    (2.00, 'Satisfactory', 'មធ្យម', 'secondary', 'Satisfactory'),
    (0.00, 'Academic Probation', 'ត្រូវតាមដានការសិក្សា', 'danger', 'Probation'),
]

SEMESTER_RANK = {'S1': 1, 'S2': 2, 'SUM': 3}


def grade_from_score(score):
    """Return the BBU letter grade for a numeric score."""
    if score is None:
        return ''
    try:
        score = float(score)
    except (TypeError, ValueError):
        return ''
    if score >= 85:
        return 'A'
    if score >= 80:
        return 'B+'
    if score >= 70:
        return 'B'
    if score >= 65:
        return 'C+'
    if score >= 50:
        return 'C'
    if score >= 45:
        return 'D'
    return 'F'


def standing_for_gpa(gpa):
    """Return English/Khmer standing labels and the badge colour for a GPA."""
    for threshold, label_en, label_kh, badge, label_short in STANDING_BANDS:
        if gpa >= threshold:
            return {
                'standing_en': label_en,
                'standing_kh': label_kh,
                'standing_badge': badge,
                'standing_short': label_short,
            }
    last = STANDING_BANDS[-1]
    return {
        'standing_en': last[1],
        'standing_kh': last[2],
        'standing_badge': last[3],
        'standing_short': last[4],
    }


def study_year_for(enrollment_date, today=None):
    """Return the current study year (1-4) based on the enrollment date."""
    if not enrollment_date:
        return 1
    today = today or date.today()
    years = (
        today.year
        - enrollment_date.year
        - ((today.month, today.day) < (enrollment_date.month, enrollment_date.day))
        + 1
    )
    return min(max(years, 1), 4)


def split_course_title(course):
    """Split a course title into English and Khmer parts."""
    if not course:
        return '', ''
    raw_title = course.title or ''
    if '(' in raw_title and ')' in raw_title:
        return (
            raw_title[:raw_title.find('(')].strip(),
            raw_title[raw_title.find('(') + 1:raw_title.rfind(')')].strip(),
        )
    return raw_title, COURSE_KHMER_MAP.get(course.code, '')


def summarize_academics(student):
    """Enrich a student's enrollments and return all academic summary values.

    Every attempt stays visible in the semester groups and transcript, but the
    cumulative GPA, earned credits and degree progress only count the latest
    attempt of each course (retakes replace earlier attempts).
    """
    enrollments = list(student.enrollments.select_related('course').all())

    # ------------------------------------------------------------------
    # Enrich every individual attempt (term views show all of them).
    # ------------------------------------------------------------------
    for enrollment in enrollments:
        grade = (enrollment.grade or '').strip().upper()
        if not grade:
            grade = grade_from_score(enrollment.score)
            enrollment.grade = grade

        enrollment.grade_point = GRADE_POINTS.get(grade, 0.0)
        credits = enrollment.course.credits if (enrollment.course and enrollment.course.credits) else 0
        enrollment.clean_en_title, enrollment.clean_kh_title = split_course_title(enrollment.course)

        if enrollment.status == 'COMPLETED':
            enrollment.credit_points = round(credits * enrollment.grade_point, 2)
            enrollment.is_passed = grade != 'F' and (
                enrollment.score is None or float(enrollment.score) >= 50
            )
        else:
            enrollment.credit_points = 0.0
            enrollment.is_passed = False

    # ------------------------------------------------------------------
    # Order attempts oldest → newest so the last one per course wins, and
    # label earlier attempts as retakes/superseded for the UI.
    # ------------------------------------------------------------------
    ordered_for_attempts = sorted(
        enrollments,
        key=lambda e: (
            e.academic_year or '',
            SEMESTER_RANK.get(e.semester, 0),
            e.enrollment_date or date.min,
            e.pk or 0,
        ),
    )
    attempt_counts = {}
    latest_by_course = {}
    for enrollment in ordered_for_attempts:
        attempt_counts[enrollment.course_id] = attempt_counts.get(enrollment.course_id, 0) + 1
        enrollment.attempt_number = attempt_counts[enrollment.course_id]
        enrollment.is_retake = enrollment.attempt_number > 1
        enrollment.is_latest_attempt = True

        earlier = latest_by_course.get(enrollment.course_id)
        if earlier is not None:
            earlier.is_latest_attempt = False
        latest_by_course[enrollment.course_id] = enrollment

    for enrollment in enrollments:
        enrollment.is_superseded = (
            not enrollment.is_latest_attempt
            and attempt_counts.get(enrollment.course_id, 0) > 1
        )
        enrollment.counts_toward_gpa = (
            enrollment.is_latest_attempt and enrollment.status == 'COMPLETED'
        )

    # ------------------------------------------------------------------
    # Cumulative totals: latest attempt of each course only.
    # ------------------------------------------------------------------
    counting_attempts = list(latest_by_course.values())
    total_credits = 0
    earned_credits = 0
    gpa_credits = 0
    total_credit_points = 0.0
    completed = []
    in_progress = []
    grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

    for enrollment in counting_attempts:
        grade = enrollment.grade
        credits = enrollment.course.credits if (enrollment.course and enrollment.course.credits) else 0
        total_credits += credits

        if enrollment.status == 'COMPLETED':
            gpa_credits += credits
            total_credit_points += enrollment.credit_points
            if enrollment.is_passed:
                earned_credits += credits
            completed.append(enrollment)
        else:
            in_progress.append(enrollment)

        if grade == 'A':
            grade_counts['A'] += 1
        elif grade in ('B', 'B+'):
            grade_counts['B'] += 1
        elif grade in ('C', 'C+'):
            grade_counts['C'] += 1
        elif grade == 'D':
            grade_counts['D'] += 1
        elif grade == 'F':
            grade_counts['F'] += 1

    scored_completed = [e for e in completed if e.score is not None]
    avg_score = (
        round(sum(float(e.score) for e in scored_completed) / len(scored_completed), 1)
        if scored_completed else 0.0
    )

    calculated_gpa = (
        round(total_credit_points / gpa_credits, 2) if gpa_credits > 0 else 0.0
    )
    stored_gpa = float(student.gpa or 0)
    effective_gpa = calculated_gpa if completed else stored_gpa

    # ------------------------------------------------------------------
    # Term grouping (all attempts remain visible within their term).
    # ------------------------------------------------------------------
    term_map = {}
    for enrollment in enrollments:
        key = (enrollment.academic_year or 'Unassigned', enrollment.semester or '')
        bucket = term_map.get(key)
        if bucket is None:
            bucket = {
                'academic_year': enrollment.academic_year or 'Unassigned',
                'semester': enrollment.semester or '',
                'semester_label': (
                    enrollment.get_semester_display()
                    if enrollment.semester else 'Unassigned term'
                ),
                'enrollments': [],
                'credits': 0,
                'earned_credits': 0,
                'credit_points': 0.0,
                'completed_count': 0,
                'in_progress_count': 0,
                'scored': [],
            }
            term_map[key] = bucket

        credits = enrollment.course.credits if (enrollment.course and enrollment.course.credits) else 0
        bucket['enrollments'].append(enrollment)
        bucket['credits'] += credits
        if enrollment.status == 'COMPLETED':
            bucket['earned_credits'] += credits
            bucket['credit_points'] += enrollment.credit_points
            bucket['completed_count'] += 1
        else:
            bucket['in_progress_count'] += 1
        if enrollment.score is not None:
            bucket['scored'].append(float(enrollment.score))

    term_groups = []
    for bucket in term_map.values():
        bucket['enrollments'].sort(key=lambda e: ((e.course.code or ''), e.pk or 0))
        bucket['count'] = len(bucket['enrollments'])
        bucket['label'] = f"{bucket['semester_label']} · {bucket['academic_year']}"
        bucket['gpa'] = (
            round(bucket['credit_points'] / bucket['earned_credits'], 2)
            if bucket['earned_credits'] else None
        )
        bucket['avg_score'] = (
            round(sum(bucket['scored']) / len(bucket['scored']), 1)
            if bucket['scored'] else None
        )
        term_groups.append(bucket)

    term_groups.sort(
        key=lambda t: (t['academic_year'], SEMESTER_RANK.get(t['semester'], 0)),
        reverse=True,
    )
    for index, bucket in enumerate(term_groups, start=1):
        bucket['anchor'] = f"term-{index}"

    summary = {
        'enrollments': enrollments,
        'term_groups': term_groups,
        'semester_count': len(term_groups),
        'total_enrolled': len(counting_attempts),
        'completed_count': len(completed),
        'in_progress_count': len(in_progress),
        'total_credits': total_credits,
        'earned_credits': earned_credits,
        'credits_pct': round(earned_credits / total_credits * 100) if total_credits else 0,
        'total_credit_points': round(total_credit_points, 2),
        'calculated_gpa': calculated_gpa,
        'effective_gpa': effective_gpa,
        'avg_score': avg_score,
        'avg_grade': grade_from_score(avg_score) if scored_completed else '',
        'grade_a_count': grade_counts['A'],
        'grade_b_count': grade_counts['B'],
        'grade_c_count': grade_counts['C'],
        'grade_d_count': grade_counts['D'],
        'grade_f_count': grade_counts['F'],
        'study_year': study_year_for(student.enrollment_date),
    }
    summary.update(standing_for_gpa(effective_gpa))
    return summary
