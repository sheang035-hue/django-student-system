"""Give every existing subject a semester so the curriculum is populated.

Known BBU course codes receive a curated semester. Any remaining subject is
alternated between Semester 1 and Semester 2 inside its study year, so no
subject is left unscheduled after the upgrade.
"""

from django.db import migrations

SEMESTER_BY_CODE = {
    'CS101': 'S1',
    'MATH101': 'S1',
    'ENG102': 'S2',
    'ACC110': 'S2',
    'WD201': 'S1',
    'DB202': 'S1',
    'PY204': 'S2',
    'NET203': 'S2',
    'UX210': 'S2',
    'SE301': 'S1',
    'AI302': 'S2',
}


def assign_semesters(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')

    for course in Course.objects.filter(semester=''):
        semester = SEMESTER_BY_CODE.get((course.code or '').upper())
        if semester:
            course.semester = semester
            course.save(update_fields=['semester'])

    # Safety net: alternate S1/S2 for any subject that is still unassigned.
    for level in ('100', '200', '300', '400'):
        remaining = list(
            Course.objects.filter(level=level, semester='').order_by('code')
        )
        for index, course in enumerate(remaining):
            course.semester = 'S1' if index % 2 == 0 else 'S2'
            course.save(update_fields=['semester'])


def clear_semesters(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Course.objects.update(semester='')


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_course_semester_course_courses_cou_level_ebe347_idx'),
    ]

    operations = [
        migrations.RunPython(assign_semesters, clear_semesters),
    ]
