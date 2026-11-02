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
    """Enrich a student's enrollments and return all academic summary values."""
    enrollments = list(student.enrollments.select_related('course').all())

    total_credits = 0
    earned_credits = 0
    total_credit_points = 0.0
    completed = []
    in_progress = []
    grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

    for enrollment in enrollments:
        grade = (enrollment.grade or '').strip().upper()
        if not grade:
            grade = grade_from_score(enrollment.score)
            enrollment.grade = grade

        enrollment.grade_point = GRADE_POINTS.get(grade, 0.0)
        credits = enrollment.course.credits if (enrollment.course and enrollment.course.credits) else 0
        enrollment.clean_en_title, enrollment.clean_kh_title = split_course_title(enrollment.course)
        total_credits += credits

        if enrollment.status == 'COMPLETED':
            enrollment.credit_points = round(credits * enrollment.grade_point, 2)
            total_credit_points += enrollment.credit_points
            earned_credits += credits
            enrollment.is_passed = grade != 'F' and (
                enrollment.score is None or float(enrollment.score) >= 50
            )
            completed.append(enrollment)
        else:
            enrollment.credit_points = 0.0
            enrollment.is_passed = False
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

    calculated_gpa = round(total_credit_points / earned_credits, 2) if earned_credits > 0 else 0.0
    stored_gpa = float(student.gpa or 0)
    effective_gpa = stored_gpa if stored_gpa > 0 else calculated_gpa

    summary = {
        'enrollments': enrollments,
        'total_enrolled': len(enrollments),
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
